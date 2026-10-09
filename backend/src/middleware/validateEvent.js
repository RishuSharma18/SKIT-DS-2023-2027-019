const VALID_EVENT_TYPES = ['entry', 'plate', 'parked', 'exit', 'wrong_parking', 'crash'];
const TRACK_ID_REQUIRED_TYPES = ['entry', 'plate', 'parked', 'exit', 'wrong_parking'];

export default function validateEvent(req, res, next) {
  const ev = req.body;

  if (!ev || typeof ev !== 'object' || Array.isArray(ev)) {
    return res.status(400).json({ error: 'Payload must be a JSON object' });
  }

  const { type, trackId, slotId, plate, vehicleType } = ev;

  if (!type || typeof type !== 'string' || !type.trim()) {
    return res.status(400).json({ error: 'Missing or empty required field: type' });
  }

  if (!VALID_EVENT_TYPES.includes(type.trim())) {
    return res.status(400).json({
      error: `Invalid event type: "${type}". Supported types: ${VALID_EVENT_TYPES.join(', ')}`,
    });
  }

  const normalizedType = type.trim();

  if (TRACK_ID_REQUIRED_TYPES.includes(normalizedType) && (trackId === undefined || trackId === null || trackId === '')) {
    return res.status(400).json({
      error: `Missing required field: trackId for event type "${normalizedType}"`,
    });
  }

  if (trackId !== undefined && trackId !== null && isNaN(Number(trackId))) {
    return res.status(400).json({
      error: 'Field "trackId" must be a valid number',
    });
  }

  if (normalizedType === 'parked' && (!slotId || typeof slotId !== 'string' || !slotId.trim())) {
    return res.status(400).json({
      error: 'Missing or empty required field: slotId for "parked" event',
    });
  }

  if (normalizedType === 'plate' && (!plate || typeof plate !== 'string' || !plate.trim())) {
    return res.status(400).json({
      error: 'Missing or empty required field: plate for "plate" event',
    });
  }

  if (vehicleType && !['bike', 'car', 'suv'].includes(vehicleType)) {
    return res.status(400).json({
      error: `Invalid vehicleType: "${vehicleType}". Allowed values: bike, car, suv`,
    });
  }

  next();
}
