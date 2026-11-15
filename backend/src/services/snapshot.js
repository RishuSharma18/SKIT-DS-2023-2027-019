import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
export const uploadsDir = path.resolve(__dirname, '../../uploads');

/**
 * Saves a base64 encoded image to the backend/uploads directory
 * and returns the relative URL (/uploads/snap-xxx.jpg).
 *
 * @param {string} snapshotData - Base64 string or Data URI
 * @returns {string|null} - URL path e.g. /uploads/snap-...jpg or null if invalid
 */
export function saveSnapshot(snapshotData) {
  if (!snapshotData || typeof snapshotData !== 'string') return null;

  const trimmed = snapshotData.trim();
  if (!trimmed) return null;

  // Already a URL or upload path
  if (trimmed.startsWith('/uploads/') || trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
    return trimmed;
  }
  if (trimmed.startsWith('uploads/')) {
    return `/${trimmed}`;
  }

  // Ensure uploads directory exists
  if (!fs.existsSync(uploadsDir)) {
    fs.mkdirSync(uploadsDir, { recursive: true });
  }

  let cleanBase64 = trimmed;
  let extension = 'jpg';

  // Check if Data URI format: data:image/<format>;base64,<data>
  const dataUriMatch = trimmed.match(/^data:image\/([a-zA-Z0-9+]+);base64,(.+)$/s);
  if (dataUriMatch) {
    const ext = dataUriMatch[1].toLowerCase();
    extension = (ext === 'jpeg' || ext === 'jpg') ? 'jpg' : ext;
    cleanBase64 = dataUriMatch[2].trim();
  } else if (trimmed.includes(';base64,')) {
    cleanBase64 = trimmed.split(';base64,')[1].trim();
  }

  // Normalize extension to jpg if jpeg
  if (extension === 'jpeg') {
    extension = 'jpg';
  }

  const randomSuffix = crypto.randomBytes(4).toString('hex');
  const filename = `snap-${Date.now()}-${randomSuffix}.${extension}`;
  const filePath = path.join(uploadsDir, filename);

  try {
    const buffer = Buffer.from(cleanBase64, 'base64');
    fs.writeFileSync(filePath, buffer);
    return `/uploads/${filename}`;
  } catch (err) {
    console.error('Failed to save snapshot file:', err.message);
    return null;
  }
}
