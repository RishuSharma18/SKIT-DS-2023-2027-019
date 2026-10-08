import mongoose from 'mongoose';

const sessionSchema = new mongoose.Schema(
  {
    trackId: { type: Number, index: true }, // temporary ID from the tracker
    cameraId: { type: String, default: 'cam-1' },
    plate: { type: String, default: null, index: true },
    vehicleType: { type: String, enum: ['bike', 'car', 'suv'], default: 'car' },
    slotId: { type: String, default: null },
    entryTime: { type: Date, default: Date.now },
    exitTime: { type: Date, default: null },
    durationSec: { type: Number, default: 0 },
    status: { type: String, enum: ['active', 'closed'], default: 'active', index: true },
    overstayAlerted: { type: Boolean, default: false },
  },
  { timestamps: true }
);

export default mongoose.model('ParkingSession', sessionSchema);
