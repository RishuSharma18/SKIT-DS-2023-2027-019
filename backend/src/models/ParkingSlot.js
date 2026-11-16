import mongoose from 'mongoose';

const slotSchema = new mongoose.Schema(
  {
    slotId: { type: String, required: true, unique: true }, // e.g. A-12
    zone: { type: String, default: 'A' },
    type: { type: String, enum: ['bike', 'car', 'suv', 'heavy_vehicle'], required: true },
    status: { type: String, enum: ['free', 'occupied', 'reserved', 'violation'], default: 'free' },
    currentSession: { type: mongoose.Schema.Types.ObjectId, ref: 'ParkingSession', default: null },
    cameraId: { type: String, default: 'cam-1' },
    polygon: {
      type: [[Number]],
      default: [],
      validate: (polygon) => polygon.length === 0 || (polygon.length >= 3
        && polygon.every((point) => point.length === 2 && point.every(Number.isFinite))),
    },
  },
  { timestamps: true }
);

export default mongoose.model('ParkingSlot', slotSchema);
