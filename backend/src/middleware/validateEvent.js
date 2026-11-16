const VALID_EVENT_TYPES = ['entry', 'plate', 'parked', 'exit', 'wrong_parking', 'crash', 'stolen_vehicle', 'occupancy'];
const TRACK_ID_REQUIRED_TYPES = ['entry', 'plate', 'parked', 'exit', 'wrong_parking'];

export default function validateEvent(req, res, next) {
  const ev = req.body;

  if (!ev || typeof ev !== 'object' || Array.isArray(ev)) {
    return res.status(400).json({ error: 'Payload must be a JSON object' });
  }

  const { type, trackId, trackIds, slotId, slots, occupiedSlotIds, sourceMode, plate, vehicleType, snapshot } = ev;

  if (!type || typeof type !== 'string' || !type.trim()) {
    return res.status(400).json({ error: 'Missing or empty required field: type' });
  }

  if (!VALID_EVENT_TYPES.includes(type.trim())) {
    return res.status(400).json({
      error: `Invalid event type: "${type}". Supported types: ${VALID_EVENT_TYPES.join(', ')}`,
    });
  }

  const normalizedType = type.trim();

  if (trackIds !== undefined) {
    if (normalizedType !== 'crash' || !Array.isArray(trackIds)
        || trackIds.length !== 2
        || trackIds.some((id) => !Number.isSafeInteger(id) || id < 0)
        || trackIds[0] === trackIds[1]) {
      return res.status(400).json({
        error: 'Field "trackIds" must contain two distinct non-negative integer IDs for a crash event',
      });
    }
  }

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

  if (normalizedType === 'occupancy') {
    const validSlots = Array.isArray(slots)
      && slots.length > 0
      && slots.length <= 500
      && slots.every((slot) => slot && typeof slot.slotId === 'string'
        && slot.slotId.trim() === slot.slotId && slot.slotId.length > 0
        && ['bike', 'car', 'suv'].includes(slot.type));
    const slotIds = validSlots ? slots.map((slot) => slot.slotId) : [];
    if (!validSlots || new Set(slotIds).size !== slotIds.length
        || !Array.isArray(occupiedSlotIds)
        || new Set(occupiedSlotIds).size !== occupiedSlotIds.length
        || occupiedSlotIds.some((id) => typeof id !== 'string' || !slotIds.includes(id))) {
      return res.status(400).json({
        error: 'Occupancy events require unique mapped slots and occupiedSlotIds contained within those slots',
      });
    }
    if (!['video', 'webcam', 'network'].includes(sourceMode)) {
      return res.status(400).json({ error: 'Occupancy sourceMode must be video, webcam, or network' });
    }
  }

  if (vehicleType && !['bike', 'car', 'suv'].includes(vehicleType)) {
    return res.status(400).json({
      error: `Invalid vehicleType: "${vehicleType}". Allowed values: bike, car, suv`,
    });
  }

  if (snapshot !== undefined && snapshot !== null && typeof snapshot !== 'string') {
    return res.status(400).json({
      error: 'Field "snapshot" must be a base64 or URL string',
    });
  }

  next();
}
