import test from 'node:test';
import assert from 'node:assert/strict';
import ParkingSlot from '../src/models/ParkingSlot.js';
import { recommendSlot } from '../src/services/allocation.js';

test('slot recommendations can be restricted to camera-mapped spaces', async () => {
  const originalFindOne = ParkingSlot.findOne;
  const filters = [];
  ParkingSlot.findOne = (filter) => {
    filters.push(filter);
    return { sort: async () => null };
  };

  try {
    assert.equal(await recommendSlot('car', ['A-04', 'A-05']), null);
    assert.deepEqual(filters, [
      { type: 'car', status: 'free', slotId: { $in: ['A-04', 'A-05'] } },
      { type: 'suv', status: 'free', slotId: { $in: ['A-04', 'A-05'] } },
    ]);
  } finally {
    ParkingSlot.findOne = originalFindOne;
  }
});
