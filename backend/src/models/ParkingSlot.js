import mongoose from 'mongoose';

const slotSchema = new mongoose.Schema(
  {
    slotId: { type: String, required: true, unique: true }, // e.g. A-12
    zone: { type: String, default: 'A' },
    type: { type: String, enum: ['bike', 'car', 'suv'], required: true },
    status: { type: String, enum: ['free', 'occupied', 'reserved'], default: 'free' },
    currentSession: { type: mongoose.Schema.Types.ObjectId, ref: 'ParkingSession', default: null },
    cameraId: { type: String, default: 'cam-1' },
  },
  { timestamps: true }
);

export default mongoose.model('ParkingSlot', slotSchema);
