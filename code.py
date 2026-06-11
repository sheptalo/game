import contextlib
import subprocess
import sys
from collections import Counter

alias_map = {
    "Fisenko Dmitriy": "Dmitriy Fisenko",
    "Dmitriy Fisenko": "Dmitriy Fisenko",
    "DFisenko": "Dmitriy Fisenko",
    "Usmanov Azamat": "Azamat Usmanov",
    "Azamat Usmanov": "Azamat Usmanov",
    "Азамат Усманов": "Azamat Usmanov",
}


def normalize_author(name):
    name = name.strip()
    for enc in ("latin-1", "cp1251"):
        with contextlib.suppress(BaseException):
            name = name.encode(enc).decode("utf-8")
    return alias_map.get(name, name)


def count_lines_by_author():
    out = subprocess.run(
        ["git", "log", "--pretty=format:@@@%an@@@", "--numstat", "--", "*.py"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    counts = Counter()
    author = None
    for line in out.splitlines():
        if line.startswith("@@@"):
            author = normalize_author(line.strip("@"))
        else:
            parts = line.split()
            if author and parts and parts[0].isdigit():
                counts[author] += int(parts[0])
    return counts


def main():
    counts = count_lines_by_author()
    if not counts:
        sys.exit("Нет данных по изменениям.")
    total = sum(counts.values())
    fmt = "{:<30} | {:>10} | {:>10} | {:>10}"

    print(fmt.format("Ник", "Строки", "Доля", "Процент"))
    print("-" * 68)
    for author, lines in counts.most_common():
        fraction = lines / total
        percent = fraction * 100
        print(fmt.format(author, lines, f"{fraction:.2f}", f"{percent:.2f}%"))
    print("-" * 68)
    print(fmt.format("Всего", total, "1.00", "100.00%"))


if __name__ == "__main__":
    main()
