import 'dotenv/config';
import http from 'http';
import { Server } from 'socket.io';
import { WebSocket, WebSocketServer } from 'ws';
import createApp from './app.js';
import connectDB from './config/db.js';
import { checkOverstays } from './services/events.js';

const app = createApp();
const server = http.createServer(app);
const webSocketServer = new WebSocketServer({ noServer: true });
const io = new Server(server, {
  cors: { origin: process.env.CLIENT_URL || '*' },
});
io.nativeWebSocketClients = webSocketServer.clients;
app.set('io', io);
io.emitWebSocket = (message) => {
  const serialized = JSON.stringify(message);
  for (const client of webSocketServer.clients) {
    if (client.readyState === WebSocket.OPEN) client.send(serialized);
  }
};

webSocketServer.on('connection', (client) => {
  client.send(JSON.stringify({
    event: 'connected',
    event_type: 'CONNECTED',
    payload: { ok: true },
  }));
});

server.on('upgrade', (request, socket, head) => {
  let pathname;
  try {
    pathname = new URL(request.url, 'http://localhost').pathname;
  } catch {
    socket.destroy();
    return;
  }
  if (pathname !== '/ws/events') return;

  const allowedOrigin = process.env.CLIENT_URL;
  const requestOrigin = request.headers.origin;
  if (allowedOrigin && allowedOrigin !== '*' && requestOrigin && requestOrigin !== allowedOrigin) {
    socket.write('HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n');
    socket.destroy();
    return;
  }
  webSocketServer.handleUpgrade(request, socket, head, (client) => {
    webSocketServer.emit('connection', client, request);
  });
});

io.on('connection', (socket) => {
  console.log('dashboard connected', socket.id);
});

const PORT = process.env.PORT || 5000;
connectDB()
  .then(() => {
    server.listen(PORT, () => console.log(`API on :${PORT}`));

    // Check for overstaying vehicles on startup and every 1 minute
    checkOverstays(io).catch((err) => console.error('Initial overstay check error:', err.message));
    setInterval(() => {
      checkOverstays(io).catch((err) => console.error('Overstay check error:', err.message));
    }, 60 * 1000);
  })
  .catch((err) => {
    console.error('DB connection failed', err.message);
    process.exit(1);
  });
