import 'dotenv/config';
import http from 'http';
import { Server } from 'socket.io';
import createApp from './app.js';
import connectDB from './config/db.js';

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
  .then(() => server.listen(PORT, () => console.log(`API on :${PORT}`)))
  .catch((err) => {
    console.error('DB connection failed', err.message);
    process.exit(1);
  });
