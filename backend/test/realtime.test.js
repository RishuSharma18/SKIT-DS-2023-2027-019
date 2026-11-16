import test from 'node:test';
import assert from 'node:assert/strict';
import { emitRealtime } from '../src/services/realtime.js';

function createRealtimeMock() {
  const socketEvents = [];
  const webSocketMessages = [];
  return {
    socketEvents,
    webSocketMessages,
    io: {
      emit: (name, payload) => socketEvents.push({ name, payload }),
      emitWebSocket: (message) => webSocketMessages.push(message),
    },
  };
}

test('broadcasts canonical exit events with the legacy event payload', () => {
  const { io, socketEvents, webSocketMessages } = createRealtimeMock();
  const session = {
    status: 'closed',
    cameraId: 'cam-1',
    trackId: 42,
    vehicleType: 'suv',
    plate: 'RJ14AB1234',
    slotId: 'B-04',
  };

  emitRealtime(io, 'session:update', session);

  assert.deepEqual(socketEvents, [{ name: 'session:update', payload: session }]);
  assert.equal(webSocketMessages.length, 1);
  const [message] = webSocketMessages;
  assert.equal(message.event, 'session:update');
  assert.equal(message.event_type, 'EXIT');
  assert.equal(message.camera_id, 'cam-1');
  assert.equal(message.track_id, 42);
  assert.equal(message.vehicle_category, 'SUV_SEDAN');
  assert.equal(message.plate_number, 'RJ14AB1234');
  assert.equal(message.slot_id, 'B-04');
  assert.match(message.event_id, /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i);
  assert.deepEqual(message.payload, session);
});

test('maps alerts and camera occupancy to shared event types', () => {
  const { io, webSocketMessages } = createRealtimeMock();

  emitRealtime(io, 'alert:new', { type: 'overstay', cameraId: 'cam-1' });
  emitRealtime(io, 'camera:occupancy', { cameraId: 'cam-1', slots: [] });

  assert.equal(webSocketMessages[0].event_type, 'ALERT');
  assert.equal(webSocketMessages[0].alert_type, 'OVERSTAY');
  assert.equal(webSocketMessages[1].event_type, 'SLOT_UPDATE');
  assert.equal(webSocketMessages[1].payload.cameraId, 'cam-1');
});
