import mongoose from 'mongoose';

export default async function connectDB() {
  const uri = process.env.MONGO_URI || 'mongodb://localhost:27017/cctv_parking';
  try {
    // Attempt standard connection with a short timeout
    await mongoose.connect(uri, { serverSelectionTimeoutMS: 2500 });
    console.log('MongoDB connected to', uri);
  } catch (err) {
    console.warn(`Local MongoDB at ${uri} unavailable (${err.message}). Starting in-memory MongoDB fallback...`);
    try {
      const { MongoMemoryServer } = await import('mongodb-memory-server');
      const mongod = await MongoMemoryServer.create();
      const memUri = mongod.getUri();
      await mongoose.connect(memUri);
      console.log('In-memory MongoDB connected to', memUri);

      // Auto-seed in-memory DB if empty
      const ParkingSlot = (await import('../models/ParkingSlot.js')).default;
      const Watchlist = (await import('../models/Watchlist.js')).default;
      const slotCount = await ParkingSlot.countDocuments();
      if (slotCount === 0) {
        const slots = [];
        for (let i = 1; i <= 12; i++) {
          const type = i <= 3 ? 'bike' : i <= 9 ? 'car' : 'suv';
          slots.push({ slotId: `A-${String(i).padStart(2, '0')}`, zone: 'A', type });
        }
        await ParkingSlot.insertMany(slots);
        await Watchlist.insertMany([
          { plate: 'RJ14AB1234', reason: 'Simulated stolen vehicle (demo)' },
          { plate: 'RJ14CD5678', reason: 'Simulated stolen vehicle (demo)' },
        ]);
        console.log(`Auto-seeded ${slots.length} slots and 2 watchlist plates into in-memory DB`);
      }
    } catch (memErr) {
      console.error('Failed to start in-memory MongoDB fallback:', memErr.message);
      throw err;
    }
  }
}
