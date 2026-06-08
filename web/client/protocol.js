import { encode, decode } from "https://cdn.jsdelivr.net/npm/@msgpack/msgpack@3.0.0/+esm";

export function encodeMessage(message) {
  return encode(message);
}

export async function decodeMessage(eventData) {
  const data = eventData instanceof Blob ? await eventData.arrayBuffer() : eventData;
  return decode(new Uint8Array(data));
}
