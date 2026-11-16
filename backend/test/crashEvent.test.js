import test from 'node:test';
import assert from 'node:assert/strict';
import validateEvent from '../src/middleware/validateEvent.js';
import Alert from '../src/models/Alert.js';

function validate(payload) {
  const result = { status: 200, body: null };
  const res = {
    status(code) {
      result.status = code;
      return this;
    },
    json(body) {
      result.body = body;
      return this;
    },
  };
  let continued = false;
  validateEvent({ body: payload }, res, () => { continued = true; });
  return { ...result, continued };
}

test('accepts crash alerts with two distinct track IDs', () => {
  assert.deepEqual(validate({
    type: 'crash',
    trackIds: [12, 34],
    message: 'Possible collision between tracks 12 and 34',
  }), { status: 200, body: null, continued: true });
});

test('continues to accept older crash events without track IDs', () => {
  assert.deepEqual(validate({ type: 'crash', message: 'Possible collision detected' }), {
    status: 200,
    body: null,
    continued: true,
  });
});

test('rejects invalid crash track ID pairs', () => {
  for (const trackIds of [[1], [1, 1], [-1, 2], [1, 1.5], ['1', 2], [1, 2, 3]]) {
    assert.equal(validate({ type: 'crash', trackIds }).status, 400, JSON.stringify(trackIds));
  }
});

test('rejects track IDs on non-crash events', () => {
  assert.equal(validate({ type: 'entry', trackId: 1, trackIds: [1, 2] }).status, 400);
});

test('accepts camera occupancy updates for configured slots', () => {
  assert.equal(validate({
    type: 'occupancy',
    sourceMode: 'network',
    slots: [{ slotId: 'A-04', type: 'car' }, { slotId: 'A-05', type: 'car' }],
    occupiedSlotIds: ['A-05'],
  }).continued, true);
});

test('rejects invalid camera occupancy updates', () => {
  for (const payload of [
    { type: 'occupancy', sourceMode: 'network', slots: [], occupiedSlotIds: [] },
    { type: 'occupancy', sourceMode: 'network', slots: [{ slotId: 'A-04', type: 'car' }, { slotId: 'A-04', type: 'car' }], occupiedSlotIds: [] },
    { type: 'occupancy', sourceMode: 'network', slots: [{ slotId: 'A-04', type: 'car' }], occupiedSlotIds: ['A-05'] },
    { type: 'occupancy', sourceMode: 'network', slots: [{ slotId: 'A-04', type: 'car' }], occupiedSlotIds: 'A-04' },
    { type: 'occupancy', sourceMode: 'unknown', slots: [{ slotId: 'A-04', type: 'car' }], occupiedSlotIds: [] },
    { type: 'occupancy', sourceMode: 'network', slots: [{ slotId: 'A-04', type: 'unicycle' }], occupiedSlotIds: [] },
  ]) {
    assert.equal(validate(payload).status, 400);
  }
});

test('stores crash track IDs on alert documents', () => {
  const alert = new Alert({ type: 'crash', trackIds: [12, 34] });
  assert.equal(alert.validateSync(), undefined);
  assert.deepEqual(alert.trackIds, [12, 34]);
});

test('defaults track IDs for other alert types', () => {
  const alert = new Alert({ type: 'wrong_parking' });
  assert.equal(alert.validateSync(), undefined);
  assert.deepEqual(alert.trackIds, []);
});
