import mongoose from 'mongoose';

const aiEventReceiptSchema = new mongoose.Schema({
  event_id: { type: String, required: true, unique: true },
  expires_at: { type: Date, required: true, expires: 0 },
}, { timestamps: true });

export default mongoose.model('AiEventReceipt', aiEventReceiptSchema);
