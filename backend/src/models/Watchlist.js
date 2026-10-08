import mongoose from 'mongoose';

const watchlistSchema = new mongoose.Schema(
  {
    plate: { type: String, required: true, unique: true, uppercase: true, trim: true },
    reason: { type: String, default: 'Reported stolen' },
    active: { type: Boolean, default: true },
  },
  { timestamps: true }
);

export default mongoose.model('Watchlist', watchlistSchema);
