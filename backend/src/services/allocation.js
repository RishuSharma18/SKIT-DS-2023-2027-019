import ParkingSlot from '../models/ParkingSlot.js';

// Which slot types can hold which vehicle category (best fit first).
// Bhumi: replace/extend with the ML-based recommender later.
const FIT = {
  bike: ['bike'],
  car: ['car', 'suv'],
  suv: ['suv'],
  heavy_vehicle: ['heavy_vehicle'],
};

export async function recommendSlot(vehicleType = 'car', slotIds = []) {
  const types = FIT[vehicleType] || FIT.car;
  for (const t of types) {
    const filter = { type: t, status: 'free' };
    if (slotIds.length) filter.slotId = { $in: slotIds };
    const slot = await ParkingSlot.findOne(filter).sort({ slotId: 1 });
    if (slot) return slot;
  }
  return null;
}
