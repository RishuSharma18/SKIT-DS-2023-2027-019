import test from 'node:test';
import assert from 'node:assert/strict';
import createApp from '../src/app.js';
import CameraZone from '../src/models/CameraZone.js';
import ParkingSlot from '../src/models/ParkingSlot.js';

test('camera zone API validates geometry and upserts without deleting other slots', async () => {
  const originals = {
    findSlots: ParkingSlot.find,
    bulkWriteSlots: ParkingSlot.bulkWrite,
    findZone: CameraZone.findOne,
    updateZone: CameraZone.findOneAndUpdate,
  };
  const writes = [];
  ParkingSlot.find = () => ({ lean: async () => [{
    slotId: 'B-04',
    type: 'suv',
    status: 'occupied',
    polygon: [[0, 0], [100, 0], [100, 80], [0, 80]],
  }] });
  ParkingSlot.bulkWrite = async (operations) => { writes.push(...operations); };
  CameraZone.findOne = () => ({ lean: async () => ({
    no_parking_zones: [],
    tripwires: [],
  }) });
  CameraZone.findOneAndUpdate = async (filter, update) => ({ filter, update });

  const server = createApp().listen(0);
  const baseUrl = await new Promise((resolve) => {
    server.once('listening', () => resolve(`http://127.0.0.1:${server.address().port}`));
  });
  const headers = { 'x-api-key': process.env.AI_API_KEY || 'dev-key' };

  try {
    const zonesResponse = await fetch(`${baseUrl}/api/v1/cameras/CAM_01/zones`, { headers });
    assert.equal(zonesResponse.status, 200);
    assert.deepEqual(await zonesResponse.json(), {
      camera_id: 'CAM_01',
      slots: [{
        slot_id: 'B-04',
        vehicle_category: 'SUV_SEDAN',
        status: 'OCCUPIED',
        polygon: [[0, 0], [100, 0], [100, 80], [0, 80]],
      }],
      no_parking_zones: [],
      tripwires: [],
    });

    const invalidResponse = await fetch(`${baseUrl}/api/v1/cameras/CAM_01/zones`, {
      method: 'PUT',
      headers: { ...headers, 'content-type': 'application/json' },
      body: JSON.stringify({ no_parking_zones: [null] }),
    });
    assert.equal(invalidResponse.status, 400);

    const geometry = {
      slots: [{
        slot_id: 'B-05',
        vehicle_category: 'HEAVY_VEHICLE',
        polygon: [[1, 1], [20, 1], [20, 20], [1, 20]],
      }],
      tripwires: [{
        tripwire_id: 'entry-line',
        event_type: 'ENTRY',
        line: [[5, 0], [5, 10]],
      }],
    };
    const updateResponse = await fetch(`${baseUrl}/api/v1/cameras/CAM_01/zones`, {
      method: 'PUT',
      headers: { ...headers, 'content-type': 'application/json' },
      body: JSON.stringify(geometry),
    });
    assert.equal(updateResponse.status, 200);
    assert.equal(writes.length, 1);
    assert.equal(writes[0].updateOne.filter.slotId, 'B-05');
    assert.equal(writes[0].updateOne.update.$set.cameraId, 'CAM_01');
    assert.deepEqual(
      writes[0].updateOne.update.$set.polygon,
      geometry.slots[0].polygon,
    );
    assert.equal(writes[0].updateOne.upsert, true);
  } finally {
    server.close();
    ParkingSlot.find = originals.findSlots;
    ParkingSlot.bulkWrite = originals.bulkWriteSlots;
    CameraZone.findOne = originals.findZone;
    CameraZone.findOneAndUpdate = originals.updateZone;
  }
});
