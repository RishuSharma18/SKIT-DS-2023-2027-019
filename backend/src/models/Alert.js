import mongoose from 'mongoose';

const alertSchema = new mongoose.Schema(
  {
    type: {
      type: String,
      enum: ['stolen_vehicle', 'crash', 'wrong_parking', 'overstay'],
      required: true,
    },
    severity: { type: String, enum: ['low', 'medium', 'high'], default: 'medium' },
    plate: { type: String, default: null },
    cameraId: { type: String, default: 'cam-1' },
    slotId: { type: String, default: null },
    message: { type: String, default: '' },
    snapshot: { type: String, default: null }, // base64 or URL (optional)
    acknowledged: { type: Boolean, default: false },
  },
  { timestamps: true }
);

export default mongoose.model('Alert', alertSchema);
