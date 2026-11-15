import express from 'express';
import cors from 'cors';
import morgan from 'morgan';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';
import routes from './routes/index.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const uploadsDir = path.resolve(__dirname, '../uploads');

// Ensure uploads directory exists
if (!fs.existsSync(uploadsDir)) {
  fs.mkdirSync(uploadsDir, { recursive: true });
}

export default function createApp() {
  const app = express();
  app.use(
    cors({
      origin: process.env.CLIENT_URL || '*',
      exposedHeaders: ['X-Total-Count'],
    })
  );
  app.use(express.json({ limit: '10mb' }));
  app.use(express.urlencoded({ extended: true, limit: '10mb' }));
  app.use('/uploads', express.static(uploadsDir));
  app.use(morgan('dev'));
  app.use('/api', routes);

  // eslint-disable-next-line no-unused-vars
  app.use((err, req, res, next) => {
    console.error(err);
    res.status(err.status || 500).json({ error: err.message });
  });
  return app;
}
