// Protects the AI -> backend ingestion endpoint.
export default function apiKey(req, res, next) {
  if (req.header('x-api-key') !== (process.env.AI_API_KEY || 'dev-key')) {
    return res.status(401).json({ error: 'Invalid API key' });
  }
  next();
}
