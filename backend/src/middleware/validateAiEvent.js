const VEHICLE_CATEGORIES = ['TWO_WHEELER', 'COMPACT_CAR', 'SUV_SEDAN', 'HEAVY_VEHICLE'];
const ALERT_TYPES = ['STOLEN_VEHICLE', 'ACCIDENT', 'WRONG_PARKING', 'OVERSTAY'];
const EVENT_TYPES = ['ENTRY', 'EXIT', 'ALERT'];
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export default function validateAiEvent(req, res, next) {
  const event = req.body;
  if (!event || typeof event !== 'object' || Array.isArray(event)) {
    return res.status(400).json({ error: 'AI event must be a JSON object' });
  }
  const requiredStrings = ['event_id', 'timestamp', 'camera_id', 'event_type'];
  if (requiredStrings.some((key) => typeof event[key] !== 'string' || !event[key].trim())) {
    return res.status(400).json({ error: 'event_id, timestamp, camera_id, and event_type are required strings' });
  }
  if (!UUID_PATTERN.test(event.event_id)) {
    return res.status(400).json({ error: 'event_id must be a UUID' });
  }
  if (Number.isNaN(Date.parse(event.timestamp))) {
    return res.status(400).json({ error: 'timestamp must be a valid ISO-8601 datetime' });
  }
  if (!EVENT_TYPES.includes(event.event_type)) {
    return res.status(400).json({ error: 'event_type must be ENTRY, EXIT, or ALERT' });
  }
  if (event.event_type !== 'ALERT' && event.alert_type != null) {
    return res.status(400).json({ error: 'alert_type must be null or omitted for non-alert events' });
  }
  if (event.track_id !== undefined
      && event.track_id !== null
      && (!Number.isSafeInteger(event.track_id) || event.track_id < 0)) {
    return res.status(400).json({ error: 'track_id must be a non-negative integer' });
  }
  if (event.related_track_ids !== undefined
      && (event.event_type !== 'ALERT'
        || event.alert_type !== 'ACCIDENT'
        || !Array.isArray(event.related_track_ids)
        || event.related_track_ids.length !== 1
        || event.related_track_ids.some((id) => !Number.isSafeInteger(id) || id < 0)
        || event.related_track_ids[0] === event.track_id)) {
    return res.status(400).json({ error: 'related_track_ids must contain one distinct track ID for ACCIDENT alerts' });
  }
  if (['ENTRY', 'EXIT'].includes(event.event_type) && event.track_id === undefined) {
    return res.status(400).json({ error: 'track_id is required for ENTRY and EXIT events' });
  }
  if (event.vehicle_category !== undefined && event.vehicle_category !== null
      && !VEHICLE_CATEGORIES.includes(event.vehicle_category)) {
    return res.status(400).json({ error: `vehicle_category must be one of ${VEHICLE_CATEGORIES.join(', ')}` });
  }
  if (event.event_type === 'ENTRY' && !event.vehicle_category) {
    return res.status(400).json({ error: 'vehicle_category is required for ENTRY events' });
  }
  if (event.plate_number !== undefined && event.plate_number !== null
      && (typeof event.plate_number !== 'string' || event.plate_number.length > 16)) {
    return res.status(400).json({ error: 'plate_number must be a string of at most 16 characters' });
  }
  if (event.plate_confidence !== undefined && event.plate_confidence !== null
      && (typeof event.plate_confidence !== 'number' || event.plate_confidence < 0 || event.plate_confidence > 1)) {
    return res.status(400).json({ error: 'plate_confidence must be between 0 and 1' });
  }
  if (event.slot_id !== undefined && event.slot_id !== null
      && (typeof event.slot_id !== 'string' || !event.slot_id.trim())) {
    return res.status(400).json({ error: 'slot_id must be a non-empty string' });
  }
  if (event.event_type === 'ALERT' && !ALERT_TYPES.includes(event.alert_type)) {
    return res.status(400).json({ error: `alert_type must be one of ${ALERT_TYPES.join(', ')} for ALERT events` });
  }
  if (event.snapshot_url !== undefined && event.snapshot_url !== null
      && (typeof event.snapshot_url !== 'string' || event.snapshot_url.length > 2048)) {
    return res.status(400).json({ error: 'snapshot_url must be a URL or relative media path' });
  }
  if (event.message !== undefined
      && (typeof event.message !== 'string' || event.message.length > 1000)) {
    return res.status(400).json({ error: 'message must be a string of at most 1000 characters' });
  }
  next();
}
