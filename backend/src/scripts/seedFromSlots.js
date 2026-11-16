// Syncs configured sample-camera polygons without deleting unrelated slots.
// Run from the backend folder: node src/scripts/seedFromSlots.js [slots.json]
import 'dotenv/config';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import mongoose from 'mongoose';
import connectDB from '../config/db.js';
import ParkingSlot from '../models/ParkingSlot.js';

const here = path.dirname(fileURLToPath(import.meta.url));
const file = process.argv[2] || path.resolve(here, '../../../ai-service/config/slots.json');

if (!fs.existsSync(file)) {
  console.error(`slots file not found: ${file}`);
  process.exit(1);
}

const { slots } = JSON.parse(fs.readFileSync(file, 'utf-8'));
if (!Array.isArray(slots) || slots.length === 0) {
  console.error('slots.json has no slots');
  process.exit(1);
}
if (slots.some((slot) => !slot.slotId || !slot.type
    || !['bike', 'car', 'suv', 'heavy_vehicle'].includes(slot.type)
    || !Array.isArray(slot.polygon) || slot.polygon.length < 3
    || slot.polygon.some((point) => !Array.isArray(point) || point.length !== 2
      || point.some((coordinate) => !Number.isFinite(coordinate))))) {
  console.error('Every slot needs a slotId, type, and polygon with at least three [x,y] points');
  process.exit(1);
}

const cameraId = process.env.CAMERA_ID || 'cam-1';
try {
  await connectDB();
  await ParkingSlot.bulkWrite(slots.map((slot) => ({
    updateOne: {
      filter: { slotId: slot.slotId },
      update: {
        $set: { cameraId, type: slot.type, polygon: slot.polygon },
        $setOnInsert: {
          slotId: slot.slotId,
          zone: slot.slotId.includes('-') ? slot.slotId.slice(0, slot.slotId.lastIndexOf('-')) : 'A',
        },
      },
      upsert: true,
    },
  })));
  console.log(`Synced ${slots.length} slot polygons for camera ${cameraId}: ${slots.map((slot) => slot.slotId).join(', ')}`);
} finally {
  await mongoose.disconnect();
}
