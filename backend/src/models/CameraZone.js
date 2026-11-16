import mongoose from 'mongoose';

const zoneSchema = new mongoose.Schema({
  zone_id: { type: String, required: true },
  polygon: {
    type: [[Number]],
    required: true,
    validate: (polygon) => polygon.length >= 3
      && polygon.every((point) => point.length === 2 && point.every(Number.isFinite)),
  },
}, { _id: false });

const tripwireSchema = new mongoose.Schema({
  tripwire_id: { type: String, required: true },
  event_type: { type: String, enum: ['ENTRY', 'EXIT'], required: true },
  line: {
    type: [[Number]],
    required: true,
    validate: (line) => line.length === 2
      && line.every((point) => point.length === 2 && point.every(Number.isFinite)),
  },
}, { _id: false });

const cameraZoneSchema = new mongoose.Schema({
  camera_id: { type: String, required: true, unique: true },
  no_parking_zones: { type: [zoneSchema], default: [] },
  tripwires: { type: [tripwireSchema], default: [] },
}, { timestamps: true });

export default mongoose.model('CameraZone', cameraZoneSchema);
