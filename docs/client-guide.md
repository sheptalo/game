# Client Developer Guide

Всё, что нужно знать, чтобы написать собственный клиент с нуля.  
Бэкенд трогать не нужно — он уже работает.

---

## Оглавление

1. [Общая архитектура](#1-общая-архитектура)
2. [Транспорт и сериализация](#2-транспорт-и-сериализация)
3. [Протокол: сообщения сервера → клиент](#3-протокол-сервер--клиент)
4. [Протокол: сообщения клиент → сервер](#4-протокол-клиент--сервер)
5. [Игровое состояние: сущности и компоненты](#5-игровое-состояние-сущности-и-компоненты)
6. [Система координат](#6-система-координат)
7. [Физика и правила симуляции](#7-физика-и-правила-симуляции)
8. [Мир: платформы и триггеры](#8-мир-платформы-и-триггеры)
9. [Главный игровой цикл клиента](#9-главный-игровой-цикл-клиента)
10. [Контрольные суммы и десинк](#10-контрольные-суммы-и-десинк)
11. [Быстрый старт — чеклист](#11-быстрый-старт--чеклист)

---

## 1. Общая архитектура

Движок работает по схеме **lockstep**:

```
Сервер                        Клиент
──────                        ──────
тикает 20 раз/сек             копирует ту же физику локально
принимает команды от игроков   отправляет команды (MOVE, JUMP)
рассылает command_frame        получает фрейм → прокручивает симуляцию
проверяет контрольные суммы    периодически отправляет checksum
```

**Ключевое правило:** клиент обязан воспроизводить физику **байт-в-байт** так же, как сервер. Если хоть один бит разошёлся — это desync. Сервер ничего не рисует; клиент рисует то, что сам насчитал.

---

## 2. Транспорт и сериализация

| Параметр | Значение |
|---|---|
| Протокол | WebSocket (бинарный) |
| Адрес по умолчанию | `ws://127.0.0.1:8766` |
| Формат сообщений | **MessagePack** |

Каждое сообщение — это словарь, упакованный в msgpack. В браузере удобно использовать библиотеку `@msgpack/msgpack`:

```js
import { encode, decode } from "https://cdn.jsdelivr.net/npm/@msgpack/msgpack@3.0.0/+esm";

// отправить
ws.send(encode({ kind: "state_sync_request" }));

// получить
ws.binaryType = "arraybuffer";
ws.addEventListener("message", async (event) => {
  const data = event.data instanceof Blob ? await event.data.arrayBuffer() : event.data;
  const message = decode(new Uint8Array(data));
  // message — обычный JS объект
});
```

---

## 3. Протокол: сервер → клиент

### `state_sync`

Приходит сразу после подключения и по запросу. Содержит полное состояние мира.

```js
{
  kind: "state_sync",
  current_tick: 482,          // текущий тик сервера
  snapshot_tick: 480,         // тик, которому соответствует snapshot
  tick_rate: 20,              // тиков в секунду
  command_delay_ticks: 3,     // задержка команд (см. раздел 9)
  checksum_interval_ticks: 100, // как часто слать checksum
  game_config: { ... },       // параметры игры (см. ниже)
  snapshot: { ... },          // состояние мира (см. раздел 5)
  command_frames: [ ... ],    // фреймы от snapshot_tick до current_tick
}
```

**game_config** — параметры симуляции, которые нужно использовать в физике:

```js
{
  player_count: 2,
  grid_columns: 11,
  spawn_start_x: 4000,       // мировые единицы × 1000 (см. раздел 6)
  spawn_start_y: 4000,
  spawn_step_x: 4000,
  spawn_step_y: 4000,
  unit_collision_width: 100,
  unit_collision_height: 200,
  move_step: 100,             // пикселей в тик по горизонтали
  jump_height: 1000,          // legacy, не используется в физике
  jump_rise_speed: 180,       // начальная скорость прыжка вверх
  jump_gravity: 18,           // замедление/ускорение за тик
  fall_speed: 100,            // максимальная скорость падения
  spawn_air_offset: 800,
}
```

---

### `command_frame`

Сервер рассылает каждый тик. Клиент применяет команды из фрейма и прокручивает симуляцию на 1 шаг.

```js
{
  kind: "command_frame",
  tick: 483,
  commands: [
    {
      type: "MOVE",
      issuer: 1,          // entity_id игрока-владельца
      sequence: 17,
      targets: [3],       // entity_id управляемых юнитов
      x: -1              // -1 = влево, 0 = стоп, 1 = вправо
    },
    {
      type: "JUMP",
      issuer: 2,
      sequence: 5,
      targets: [4]
    }
  ]
}
```

Если `commands` пустой — тик просто прокручивается без команд (всё равно нужно вызвать шаг физики).

---

### `command_accepted`

Подтверждение того, что сервер принял команду.

```js
{
  kind: "command_accepted",
  sequence: 17,           // sequence из отправленной команды
  assigned_tick: 486,     // тик, в котором команда будет применена
}
```

---

### `desync_report`

Кто-то насчитал другую контрольную сумму.

```js
{
  kind: "desync_report",
  tick: 400,
  checksums: {
    "a3f9c120": ["p1"],    // хэш → список игроков с этим хэшем
    "ff001234": ["p2"]
  }
}
```

При получении — запросите `state_sync_request`, чтобы вернуться к консистентному состоянию.

---

### `error`

```js
{ kind: "error", detail: "Unknown command type: 'FOO'" }
```

---

## 4. Протокол: клиент → сервер

### Отправить команду

```js
ws.send(encode({
  kind: "command",
  command: {
    type: "MOVE",          // или "JUMP"
    issuer: 1,             // entity_id вашего игрока (не юнита)
    sequence: 42,          // монотонно растущий номер
    targets: [3],          // entity_id юнита, которым управляете
    x: 1,                  // только для MOVE: -1 | 0 | 1
  }
}));
```

> **issuer** — это id **игрока** (голая сущность без компонентов, владелец юнита).  
> **targets** — id **юнита** (сущность с Position, Collision и т.д.).  
> Сервер проверяет, что `OwnedBy.owner === issuer`, иначе команда игнорируется.

### Запросить resync

```js
ws.send(encode({ kind: "state_sync_request" }));
```

### Отправить контрольную сумму

```js
ws.send(encode({
  kind: "checksum",
  player_id: "p1",        // строка: "p1", "p2", ...
  tick: 400,
  checksum: "a3f9c120",   // 8 hex символов (FNV-1a, см. раздел 10)
}));
```

---

## 5. Игровое состояние: сущности и компоненты

Мир — это список сущностей. Каждая сущность — объект с полем `id` и набором компонентов.

```js
// snapshot.entities — массив:
[
  { id: 1 },                          // голый игрок (владелец)
  { id: 2 },
  {
    id: 3,                            // юнит игрока 1
    OwnedBy: { owner: 1 },
    Position: { x: 4000, y: 4800 },
    Movement: { x: 0, y: 0 },
    Collision: { width: 100, height: 200 },
    RigidBody: { vy: 0, jump_remaining: 0 },
    TriggerOverlap: { inside: [] },
  },
  {
    id: 5,                            // платформа
    Position: { x: 4000, y: 3650 },
    Collision: { width: 8000, height: 100 },
  },
  {
    id: 6,                            // триггер-зона
    Position: { x: 3000, y: 4550 },
    Collision: { width: 100, height: 1500 },
    Trigger: { on_enter: "teleport", on_exit: "" },
  }
]
```

### Справочник компонентов

| Компонент | Поля | Смысл |
|---|---|---|
| `Position` | `x, y` | Центр сущности (fixed-point, ÷1000 = мировые единицы) |
| `Collision` | `width, height` | Размер AABB-хитбокса (тоже ÷1000) |
| `Movement` | `x, y` | Текущий вектор движения: x ∈ {-1,0,1}, y ∈ {0,1} |
| `RigidBody` | `vy, jump_remaining` | Физическое состояние: `vy` — скорость по Y, знаковая |
| `OwnedBy` | `owner` | entity_id игрока-владельца |
| `Trigger` | `on_enter, on_exit` | Имена событий при пересечении зоны |
| `TriggerOverlap` | `inside` | Список id триггеров, в которых юнит сейчас находится |

**Как понять, что это за сущность:**

| Что есть | Кто это |
|---|---|
| Нет компонентов кроме `id` | Игрок-владелец (issuer для команд) |
| `OwnedBy` + `Position` + `RigidBody` | Управляемый юнит |
| `Position` + `Collision`, без `Trigger` | Статическая платформа |
| `Trigger` присутствует | Триггер-зона (невидимая) |

---

## 6. Система координат

Все числа в мире — **целые числа, умноженные на 1000** (fixed-point с тремя знаками после запятой). Это сделано для детерминизма: никакой плавающей точки в симуляции.

```
world unit = raw_value / 1000
screen_x   = world_x * TILE_SIZE - camera.x
screen_y   = view_height - world_y * TILE_SIZE + camera.y
```

**Ось Y направлена вверх** (как в математике, не как в CSS). `y=0` — низ мира, `y > 0` — выше.

```js
const TILE_SIZE = 40;  // пикселей на мировую единицу

function worldToScreen(camera, worldX, worldY, viewHeight) {
  return {
    x: worldX * TILE_SIZE - camera.x,
    y: viewHeight - worldY * TILE_SIZE + camera.y,
  };
}

// Перевод raw → world
function unfixed(raw) { return raw / 1000; }
```

**AABB юнита** с центром в `(pos.x, pos.y)` и размером `(col.width, col.height)`:

```
left   = pos.x - col.width  / 2
right  = pos.x + col.width  / 2
bottom = pos.y - col.height / 2
top    = pos.y + col.height / 2
```

Всё в raw-единицах, деление — целочисленное (`Math.floor`).

---

## 7. Физика и правила симуляции

Симуляция — это детерминированная функция: `state × commands → state`. Вы обязаны воспроизводить её точно.

### Порядок обработки за один тик

```
для каждого юнита (в порядке возрастания entity id):
  1. применить команду MOVE → обновить movement.x
  2. применить команду JUMP → установить movement.y = 1
  3. разрешить горизонтальное движение (resolve x)
  4. проверить is_grounded
  5. если jump-команда была и is_grounded → vy = jump_rise_speed
  6. сбросить movement.y = 0
  7. разрешить вертикальное движение (vy → resolve y)
  8. обновить vy для следующего тика

затем: обработать триггеры (enter/exit)
```

> Препятствия (obstacles) снимаются **один раз в начале тика** и не обновляются, пока тик не закончится. Это критично: юниты не видят позиций друг друга после их движения в этом же тике.

---

### Горизонтальное движение

```js
// delta = movement.x * move_step  (-100, 0, или +100)
position.x = resolveAxis(position, collision, obstacles, id, "x", delta);
```

`resolveAxis` двигает сущность вплотную к ближайшей стене, не проникая внутрь.

---

### Вертикальная физика (прыжок + гравитация)

```js
// 1. Инициация прыжка (только если стоит на земле)
if (jumpCommand && isGrounded) {
  rigidbody.vy = game_config.jump_rise_speed; // = 180
}

// 2. Применяем физику
if (rigidbody.vy > 0) {
  // Фаза подъёма: двигаем вверх, гравитация тормозит
  const oldY = position.y;
  position.y = resolveAxis(..., "y", rigidbody.vy);
  if (position.y === oldY) {
    // Потолок — убиваем скорость
    rigidbody.vy = 0;
  } else {
    rigidbody.vy = Math.max(0, rigidbody.vy - game_config.jump_gravity); // -18 каждый тик
  }
} else if (!isGrounded) {
  // Фаза падения: ускоряемся вниз до fall_speed
  rigidbody.vy = Math.max(-game_config.fall_speed, rigidbody.vy - game_config.jump_gravity);
  position.y = resolveAxis(..., "y", rigidbody.vy); // delta отрицательная
} else {
  // На земле, покоимся
  rigidbody.vy = 0;
}
```

**Форма дуги прыжка** при `jump_rise_speed=180, jump_gravity=18`:

```
Тик:  0    1    2    3    4    5    6    7    8    9    10
vy:   180  162  144  126  108  90   72   54   36   18   0  → начало падения
```

Высота около 990 raw-единиц ≈ 1 мировая единица.

---

### Проверка «стоит на земле» (`isGrounded`)

Юнит считается на земле, если прямо под его нижним краем (с допуском ±1) есть препятствие с совпадающим X-диапазоном:

```js
function isGrounded(entityId, position, collision, obstacles) {
  const halfW = Math.floor(collision.width / 2);
  const halfH = Math.floor(collision.height / 2);
  const left   = position.x - halfW;
  const right  = position.x + halfW;
  const bottom = position.y - halfH;
  for (const [otherId, oLeft, oRight, , oTop] of obstacles) {
    if (otherId === entityId) continue;
    if (left >= oRight || right <= oLeft) continue;  // нет X-пересечения
    if (bottom - 1 <= oTop && oTop <= bottom + 1) return true;
  }
  return false;
}
```

---

### Триггеры

После движения всех юнитов система проверяет пересечения с триггер-зонами:

- Если юнит **вошёл** в зону (`on_enter`): выполняется соответствующее событие
- Если юнит **вышел** из зоны (`on_exit`): выполняется соответствующее событие

Список активных зон хранится в `TriggerOverlap.inside` (массив id триггеров).

**Встроенные события:**

| Имя | Что происходит |
|---|---|
| `teleport` | Юнит перемещается в `(0, 0)` |
| `spawn` | Юнит перемещается в `(5000, 5000)` |

---

## 8. Мир: платформы и триггеры

Мир создаётся сервером при старте на основе `game_config`. При `spawn_start_x=4000, spawn_start_y=4000`:

```
Сущность         Центр (raw)         Размер (raw)     Тип
─────────────────────────────────────────────────────────────
Земля            (4000, 3650)        8000 × 100        платформа (floor)
Верхняя плат. 1  (6000, 4550)         800 × 100        платформа (elevated)
Верхняя плат. 2  (4000, 4550)         800 × 100        платформа (elevated)
Стена-телепорт   (3000, 4550)         100 × 1500       триггер on_enter="teleport"
Яма-спавн        (4000, −5000)     100000 × 1          триггер on_enter="spawn"
```

> Y земли = `spawn_start_y − unit_collision_height/2 − 50` = `4000 − 100 − 50 = 3850`.  
> Юнит спавнится на `spawn_start_y + spawn_air_offset = 4000 + 800 = 4800` (в воздухе, падает на землю).

**Правила:**
- Сущности **без компонента `Trigger`** — твёрдые стены/пол. Юниты не проходят сквозь них.
- Сущности **с `Trigger`** — призрачные зоны. Коллизии физически нет, только событие.

---

## 9. Главный игровой цикл клиента

### Подключение

```
1. ws = new WebSocket("ws://127.0.0.1:8766")
2. Сервер сразу шлёт state_sync
3. Применяем state_sync:
   - сохраняем snapshot как текущее состояние мира
   - запоминаем tick_rate, command_delay_ticks, checksum_interval_ticks, game_config
   - прокручиваем command_frames (от snapshot_tick до current_tick)
   - сбрасываем счётчик sequence = 0
```

### Каждый тик (при получении `command_frame`)

```
1. Если frame.tick > state.simTick:
   - прокрутить пустые тики (без команд) до frame.tick
2. Применить команды из фрейма к movement компонентам юнитов
3. Прокрутить физику (movement → resolve x → check grounded → jump/fall → resolve y)
4. Обработать триггеры
5. Если (simTick % checksum_interval_ticks === 0): отправить checksum
6. simTick++
```

### Команды и задержка

Команды не применяются мгновенно. Когда игрок нажал кнопку:

```
1. Отправить { kind: "command", command: { ..., sequence: N } }
2. Сервер принимает, назначает тик = current_tick + command_delay_ticks (=3)
3. Возвращает command_accepted { sequence: N, assigned_tick: T }
4. В тике T команда появится в command_frame и будет применена всеми клиентами
```

Это значит: между нажатием и реакцией юнита всегда 3 тика (≈150 мс при 20 TPS). Это нормально — так обеспечивается детерминизм.

### Управление вводом

Рекомендуется **не слать команду на каждое нажатие клавиши**, а слать только при смене направления (throttle ≈50 мс). Иначе очередь ACK разрастается.

```js
// Пример: слать MOVE только если направление изменилось
let lastDirection = "0";
setInterval(() => {
  const dir = getDirection(); // -1, 0, или 1
  if (String(dir) !== lastDirection) {
    sendMove(unit, dir);
    lastDirection = String(dir);
  }
}, 50);
```

---

## 10. Контрольные суммы и десинк

Каждые `checksum_interval_ticks` тиков (обычно 100) клиент считает хэш состояния и отправляет его серверу. Сервер собирает хэши от всех клиентов и, если они расходятся, рассылает `desync_report`.

### Алгоритм (FNV-1a, 32 бита)

```js
function checksum(tick, snapshot) {
  let hash = 2166136261; // FNV offset basis

  function addText(text) {
    for (const char of text) {
      hash ^= char.charCodeAt(0);
      hash = Math.imul(hash, 16777619) >>> 0; // FNV prime, unsigned
    }
  }

  function addInt(n) { addText(`i:${n};`); }
  function addStr(s) { addText(`s:${s.length}:${s};`); }

  function writeValue(v) {
    if (typeof v === "boolean") { addStr("bool"); addInt(v ? 1 : 0); }
    else if (typeof v === "number") { addStr("int"); addInt(v); }
    else { addStr("str"); addStr(String(v)); }
  }

  function writeComponent(name, payload) {
    addStr(name);
    for (const field of Object.keys(payload).sort()) {
      addStr(field);
      writeValue(payload[field]);
    }
  }

  addInt(tick);
  addInt(snapshot.next_entity_id);
  for (const entity of [...snapshot.entities].sort((a, b) => a.id - b.id)) {
    addInt(entity.id);
    for (const key of Object.keys(entity).filter(k => k !== "id").sort()) {
      writeComponent(key, entity[key]);
    }
  }

  return hash.toString(16).padStart(8, "0"); // например "a3f9c120"
}
```

### Реакция на десинк

```js
if (message.kind === "desync_report") {
  // Если наш player_id упомянут в report — просим полную синхронизацию
  ws.send(encode({ kind: "state_sync_request" }));
}
```

После получения `state_sync` — полностью заменить локальное состояние и прокрутить command_frames заново.

---

## 11. Быстрый старт — чеклист

- [ ] Подключиться по WebSocket, распарсить бинарный msgpack
- [ ] При `state_sync`: записать snapshot, прокрутить command_frames до `current_tick`
- [ ] Определить своего игрока по слоту (`p1` / `p2`) → найти сущность с `OwnedBy.owner = playerEntityId(slot)`
- [ ] При `command_frame`: прокрутить симуляцию до нужного тика, применить команды, выполнить физику
- [ ] Рендерить позиции юнитов и платформ (у триггеров `Trigger` — не рисовать)
- [ ] Отправлять MOVE при смене направления, JUMP при нажатии
- [ ] Считать и отправлять checksum каждые 100 тиков
- [ ] При `desync_report` — слать `state_sync_request`

### Как найти своего юнита

```js
// slot = "p1" | "p2" | ...
function playerEntityId(slot) {
  const num = parseInt(slot.slice(1), 10); // "p1" → 1
  return num; // entity id игрока-владельца (1, 2, ...)
}

function myUnit(snapshot, slot) {
  const ownerId = playerEntityId(slot);
  return snapshot.entities.find(e => e.OwnedBy?.owner === ownerId);
}
```

### Минимальный скелет

```js
const ws = new WebSocket("ws://127.0.0.1:8766");
ws.binaryType = "arraybuffer";

let state = null;

ws.addEventListener("message", async (event) => {
  const msg = decode(new Uint8Array(event.data));

  if (msg.kind === "state_sync") {
    state = buildInitialState(msg);        // применить snapshot
    applyCommandFrames(state, msg.command_frames); // догнать до current_tick
    return;
  }

  if (msg.kind === "command_frame") {
    applyFrame(state, msg);               // команды + физика + триггеры
    maybeSendChecksum(state, ws);
    render(state);
    return;
  }

  if (msg.kind === "desync_report") {
    ws.send(encode({ kind: "state_sync_request" }));
  }
});

document.addEventListener("keydown", (e) => {
  if (!state) return;
  if (e.key === "ArrowRight") sendMove(ws, state, 1);
  if (e.key === "ArrowLeft")  sendMove(ws, state, -1);
  if (e.key === "ArrowUp")    sendJump(ws, state);
});
```
