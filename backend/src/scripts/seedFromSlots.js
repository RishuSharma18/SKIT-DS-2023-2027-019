// Makes the database slots match ai-service/config/slots.json.
// Run from the backend folder:  node src/scripts/seedFromSlots.js
// WARNING: replaces ALL parking slots in the database (watchlist is not touched).
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

await connectDB();
await ParkingSlot.deleteMany({});
await ParkingSlot.insertMany(
  slots.map((s) => ({ slotId: s.slotId, zone: s.slotId.split('-')[0], type: s.type }))
);
console.log(`Database now has ${slots.length} slots: ${slots.map((s) => `${s.slotId}(${s.type})`).join(', ')}`);
await mongoose.disconnect();
