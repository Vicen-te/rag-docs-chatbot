// Parse a buffer of raw SSE text into discrete events. Returns the
// list of complete events and the leftover (partial) tail to keep for
// the next chunk.
//
// SSE strips a single leading space after "data:"; trailing whitespace
// must be preserved so streamed tokens keep their word breaks.
export function parseSseChunk(buffer) {
  const parts = buffer.split('\n\n');
  const leftover = parts.pop();
  const events = [];
  for (const raw of parts) {
    if (!raw.trim()) continue;
    let event = 'message';
    let data = '';
    for (const line of raw.split('\n')) {
      if (line.startsWith('event:')) {
        event = line.slice(6).trim();
      } else if (line.startsWith('data:')) {
        const v = line.slice(5);
        data += v.startsWith(' ') ? v.slice(1) : v;
      }
    }
    events.push({ event, data });
  }
  return [events, leftover];
}
