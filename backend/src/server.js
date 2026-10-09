import 'dotenv/config';
import http from 'http';
import { Server } from 'socket.io';
import createApp from './app.js';
import connectDB from './config/db.js';
import { checkOverstays } from './services/events.js';

const app = createApp();
const server = http.createServer(app);
const io = new Server(server, {
  cors: { origin: process.env.CLIENT_URL || '*' },
});
app.set('io', io);

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
