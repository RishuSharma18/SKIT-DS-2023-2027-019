import ParkingSlot from '../models/ParkingSlot.js';

// Which slot types can hold which vehicle category (best fit first).
// Bhumi: replace/extend with the ML-based recommender later.
const FIT = { bike: ['bike'], car: ['car', 'suv'], suv: ['suv'] };

export async function recommendSlot(vehicleType = 'car') {
  const types = FIT[vehicleType] || FIT.car;
  for (const t of types) {
    const slot = await ParkingSlot.findOne({ type: t, status: 'free' }).sort({ slotId: 1 });
    if (slot) return slot;
  }
  return null;
}
