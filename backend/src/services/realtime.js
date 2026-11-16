export function emitRealtime(io, event, payload) {
  io.emit(event, payload);
  if (typeof io.emitWebSocket === 'function') {
    io.emitWebSocket({ event, payload });
  }
}
