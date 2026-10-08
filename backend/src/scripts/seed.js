import 'dotenv/config';
import mongoose from 'mongoose';
import ParkingSlot from '../models/ParkingSlot.js';
import Watchlist from '../models/Watchlist.js';

await mongoose.connect(process.env.MONGO_URI || 'mongodb://localhost:27017/cctv_parking');

const slots = [];
for (let i = 1; i <= 12; i++) {
  const type = i <= 3 ? 'bike' : i <= 9 ? 'car' : 'suv';
  slots.push({ slotId: `A-${String(i).padStart(2, '0')}`, zone: 'A', type });
}
await ParkingSlot.deleteMany({});
await ParkingSlot.insertMany(slots);

await Watchlist.deleteMany({});
await Watchlist.insertMany([
  { plate: 'RJ14AB1234', reason: 'Simulated stolen vehicle (demo)' },
  { plate: 'RJ14CD5678', reason: 'Simulated stolen vehicle (demo)' },
]);

console.log(`Seeded ${slots.length} slots and 2 watchlist plates`);
await mongoose.disconnect();
