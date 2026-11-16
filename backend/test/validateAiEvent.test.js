import test from 'node:test';
import assert from 'node:assert/strict';
import validateAiEvent from '../src/middleware/validateAiEvent.js';

function validate(payload) {
  const result = { status: 200, body: null, continued: false };
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
  validateAiEvent({ body: payload }, res, () => { result.continued = true; });
  return result;
}

const event = {
  event_id: 'fc3fb6b5-31a4-4d7b-bf3e-01ef7b17583e',
  timestamp: '2025-01-15T10:00:00.000Z',
  camera_id: 'CAM_01',
  track_id: 42,
  vehicle_category: 'SUV_SEDAN',
  event_type: 'ENTRY',
  slot_id: 'B-04',
};

test('accepts a canonical entry event and related collision track', () => {
  assert.equal(validate(event).continued, true);
  assert.equal(validate({ ...event, alert_type: 'ACCIDENT' }).status, 400);
  assert.equal(validate({
    ...event,
    event_type: 'ALERT',
    alert_type: 'ACCIDENT',
    related_track_ids: [43],
  }).continued, true);
});

test('rejects invalid canonical categories and malformed related track IDs', () => {
  assert.equal(validate({ ...event, vehicle_category: 'CAR' }).status, 400);
  assert.equal(validate({
    ...event,
    event_type: 'ALERT',
    alert_type: 'ACCIDENT',
    related_track_ids: [42],
  }).status, 400);
  assert.equal(validate({
    ...event,
    event_type: 'ALERT',
    alert_type: 'ACCIDENT',
    related_track_ids: [43, 44],
  }).status, 400);
});
