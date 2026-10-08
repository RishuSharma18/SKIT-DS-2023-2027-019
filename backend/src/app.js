import express from 'express';
import cors from 'cors';
import morgan from 'morgan';
import routes from './routes/index.js';

export default function createApp() {
  const app = express();
  app.use(cors({ origin: process.env.CLIENT_URL || '*' }));
  app.use(express.json({ limit: '2mb' }));
  app.use(morgan('dev'));
  app.use('/api', routes);

  // eslint-disable-next-line no-unused-vars
  app.use((err, req, res, next) => {
    console.error(err);
    res.status(err.status || 500).json({ error: err.message });
  });
  return app;
}
