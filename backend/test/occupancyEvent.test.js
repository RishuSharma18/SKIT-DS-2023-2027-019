import test from 'node:test';
import assert from 'node:assert/strict';
import ParkingSlot from '../src/models/ParkingSlot.js';
import { handleEvent } from '../src/services/events.js';

test('occupancy event updates only mapped slots and emits current slot state', async () => {
  const originalBulkWrite = ParkingSlot.bulkWrite;
  const originalFind = ParkingSlot.find;
  let operations;
  const emitted = [];
  ParkingSlot.bulkWrite = async (updates) => { operations = updates; };
  ParkingSlot.find = (filter) => {
    if (filter) {
      return Promise.resolve([
        { slotId: 'A-04', status: 'occupied', currentSession: 'stale-session' },
        { slotId: 'A-05', status: 'free', currentSession: null },
      ]);
    }
    return { sort: async () => [{ slotId: 'A-04', status: 'free' }] };
  };

  try {
    await handleEvent({ emit: (name, value) => emitted.push({ name, value }) }, {
      type: 'occupancy',
      cameraId: 'cam-1',
      sourceMode: 'network',
      slots: [{ slotId: 'A-04', type: 'car' }, { slotId: 'A-05', type: 'car' }],
      occupiedSlotIds: ['A-05'],
      detectionSummary: { total: 3, bikes: 1, cars: 2 },
    });

    assert.deepEqual(operations, [
      { updateOne: {
        filter: { slotId: 'A-04' },
        update: {
          $setOnInsert: { slotId: 'A-04', zone: 'A', type: 'car', cameraId: 'cam-1' },
          $set: { status: 'free', currentSession: null },
        },
        upsert: true,
      } },
      { updateOne: {
        filter: { slotId: 'A-05' },
        update: {
          $setOnInsert: { slotId: 'A-05', zone: 'A', type: 'car', cameraId: 'cam-1', currentSession: null },
          $set: { status: 'occupied' },
        },
        upsert: true,
      } },
    ]);
    assert.equal(emitted[0].name, 'slots:update');
    assert.deepEqual(emitted[1], {
      name: 'camera:occupancy',
      value: {
        cameraId: 'cam-1',
        slots: [{ slotId: 'A-04', type: 'car' }, { slotId: 'A-05', type: 'car' }],
        slotIds: ['A-04', 'A-05'],
        occupiedSlotIds: ['A-05'],
        detectionSummary: { total: 3, bikes: 1, cars: 2 },
        sourceMode: 'network',
      },
    });
  } finally {
    ParkingSlot.bulkWrite = originalBulkWrite;
    ParkingSlot.find = originalFind;
  }
});

test('sample video occupancy updates broadcast estimates without saving slot state', async () => {
  const originalBulkWrite = ParkingSlot.bulkWrite;
  const emitted = [];
  ParkingSlot.bulkWrite = async () => { throw new Error('Replay occupancy must not update the database'); };

  try {
    const result = await handleEvent({ emit: (name, value) => emitted.push({ name, value }) }, {
      type: 'occupancy',
      cameraId: 'cam-1',
      sourceMode: 'video',
      slots: [{ slotId: 'A-04', type: 'car' }],
      occupiedSlotIds: ['A-04'],
      detectionSummary: { total: 2, bikes: 0, cars: 2 },
    });

    assert.deepEqual(result, { slots: ['A-04'], persisted: false });
    assert.deepEqual(emitted, [{
      name: 'camera:occupancy',
      value: {
        cameraId: 'cam-1',
        slots: [{ slotId: 'A-04', type: 'car' }],
        slotIds: ['A-04'],
        occupiedSlotIds: ['A-04'],
        detectionSummary: { total: 2, bikes: 0, cars: 2 },
        sourceMode: 'video',
      },
    }]);
  } finally {
    ParkingSlot.bulkWrite = originalBulkWrite;
  }
});
