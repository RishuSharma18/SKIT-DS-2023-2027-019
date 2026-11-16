import ParkingSession from '../models/ParkingSession.js';
import ParkingSlot from '../models/ParkingSlot.js';
import Watchlist from '../models/Watchlist.js';
import Alert from '../models/Alert.js';
import { recommendSlot } from './allocation.js';
import { saveSnapshot } from './snapshot.js';
import { emitRealtime } from './realtime.js';

async function raiseAlert(io, data) {
  if (data.snapshot && typeof data.snapshot === 'string') {
    data.snapshot = saveSnapshot(data.snapshot);
  }
  const alert = await Alert.create(data);
  emitRealtime(io, 'alert:new', alert);
  return alert;
}

async function checkWatchlist(io, plate, cameraId, slotId, snapshot) {
  if (!plate) return;
  const hit = await Watchlist.findOne({ plate, active: true });
  if (hit) {
    await raiseAlert(io, {
      type: 'stolen_vehicle',
      severity: 'high',
      plate,
      cameraId,
      slotId,
      message: `Watchlist match: ${plate} (${hit.reason})`,
      snapshot: snapshot || null,
    });
  }
}

async function emitSlots(io) {
  emitRealtime(io, 'slots:update', await ParkingSlot.find().sort({ slotId: 1 }));
}

/**
 * Handles one event from the AI service.
 * type: entry | plate | parked | exit | wrong_parking | crash | stolen_vehicle
 */
export async function handleEvent(io, ev) {
  const { type, trackId, cameraId = 'cam-1', plate = null, vehicleType = 'car', slotId = null } = ev;

  switch (type) {
    case 'entry': {
      const rec = await recommendSlot(vehicleType);
      let session = await ParkingSession.findOne({ trackId, cameraId, status: 'active' }).sort({ createdAt: -1 });
      if (session) {
        session.plate = plate || session.plate;
        session.vehicleType = vehicleType || session.vehicleType;
        session.slotId = slotId || session.slotId;
        await session.save();
        emitRealtime(io, 'session:update', session);
      } else {
        session = await ParkingSession.create({
          trackId, cameraId, plate, vehicleType, slotId,
          entryTime: ev.timestamp ? new Date(ev.timestamp) : new Date(),
        });
        emitRealtime(io, 'session:new', session);
      }
      await checkWatchlist(io, plate, cameraId, null, ev.snapshot);
      return { session, recommendedSlot: rec ? rec.slotId : null };
    }
    case 'plate': {
      const session = await ParkingSession.findOneAndUpdate(
        { trackId, cameraId, status: 'active' }, { plate }, { new: true, sort: { createdAt: -1 } }
      );
      await checkWatchlist(io, plate, cameraId, session?.slotId ?? null, ev.snapshot);
      if (session) emitRealtime(io, 'session:update', session);
      return { session };
    }
    case 'parked': {
      const session = await ParkingSession.findOneAndUpdate(
        { trackId, cameraId, status: 'active' }, { slotId }, { new: true, sort: { createdAt: -1 } }
      );
      if (slotId) {
        await ParkingSlot.updateOne(
          { slotId }, { status: 'occupied', currentSession: session?._id ?? null }
        );
        await emitSlots(io);
      }
      return { session };
    }
    case 'exit': {
      const session = await ParkingSession.findOne({ trackId, cameraId, status: 'active' }).sort({ createdAt: -1 });
      if (!session) return { session: null };
      session.exitTime = ev.timestamp ? new Date(ev.timestamp) : new Date();
      session.durationSec = Math.round((session.exitTime - session.entryTime) / 1000);
      session.status = 'closed';
      await session.save();
      if (session.slotId) {
        await ParkingSlot.updateOne({ slotId: session.slotId }, { status: 'free', currentSession: null });
        await emitSlots(io);
      }
      emitRealtime(io, 'session:update', session);
      return { session };
    }
    case 'occupancy': {
      const slotIds = ev.slots.map((slot) => slot.slotId);
      if (ev.sourceMode === 'video') {
        emitRealtime(io, 'camera:occupancy', {
          cameraId,
          slots: ev.slots,
          slotIds,
          occupiedSlotIds: ev.occupiedSlotIds,
          detectionSummary: ev.detectionSummary ?? null,
          sourceMode: ev.sourceMode,
        });
        return { slots: slotIds, persisted: false };
      }

      const occupiedSlotIds = new Set(ev.occupiedSlotIds);
      const currentSlots = await ParkingSlot.find({ slotId: { $in: slotIds } });
      const currentById = new Map(currentSlots.map((slot) => [slot.slotId, slot]));
      const slotsById = new Map(ev.slots.map((slot) => [slot.slotId, slot]));
      const updates = slotIds.flatMap((id) => {
        const current = currentById.get(id);
        const occupied = occupiedSlotIds.has(id);
        if (current && !occupied && current.status === 'reserved') return [];
        if (current && current.status === (occupied ? 'occupied' : 'free')
            && (occupied || current.currentSession == null)) return [];

        const slot = slotsById.get(id);
        const update = {
          $setOnInsert: {
            slotId: id,
            zone: id.includes('-') ? id.slice(0, id.lastIndexOf('-')) : 'A',
            type: slot.type,
            cameraId,
          },
          $set: { status: occupied ? 'occupied' : 'free' },
        };
        if (occupied) update.$setOnInsert.currentSession = null;
        else update.$set.currentSession = null;
        return [{ updateOne: { filter: { slotId: id }, update, upsert: true } }];
      });
      if (updates.length) {
        await ParkingSlot.bulkWrite(updates);
        await emitSlots(io);
      }
      emitRealtime(io, 'camera:occupancy', {
        cameraId,
        slots: ev.slots,
        slotIds,
        occupiedSlotIds: ev.occupiedSlotIds,
        detectionSummary: ev.detectionSummary ?? null,
        sourceMode: ev.sourceMode,
      });
      return { slots: slotIds, persisted: true };
    }
    case 'wrong_parking':
      return { alert: await raiseAlert(io, {
        type: 'wrong_parking', severity: 'medium', plate, cameraId, slotId,
        message: ev.message || 'Vehicle parked outside a valid slot / blocking path',
        snapshot: ev.snapshot || null,
      }) };
    case 'crash':
      return { alert: await raiseAlert(io, {
        type: 'crash', severity: 'high', plate, cameraId,
        trackIds: ev.trackIds || [],
        message: ev.message || 'Possible collision detected',
        snapshot: ev.snapshot || null,
      }) };
    case 'stolen_vehicle':
      return { alert: await raiseAlert(io, {
        type: 'stolen_vehicle', severity: 'high', plate, cameraId, slotId,
        message: ev.message || `Stolen vehicle detected${plate ? `: ${plate}` : ''}`,
        snapshot: ev.snapshot || null,
      }) };
    default: {
      const err = new Error(`Unknown event type: ${type}`);
      err.status = 400;
      throw err;
    }
  }
}

// Sprint 5: call on an interval from server.js to flag long stays.
export async function checkOverstays(io) {
  const limitMs = (Number(process.env.OVERSTAY_HOURS) || 4) * 3600 * 1000;
  const cutoff = new Date(Date.now() - limitMs);
  const stale = await ParkingSession.find({
    status: 'active', overstayAlerted: false, entryTime: { $lt: cutoff },
  });
  for (const s of stale) {
    await raiseAlert(io, {
      type: 'overstay', severity: 'low', plate: s.plate, slotId: s.slotId,
      message: `Vehicle exceeded ${process.env.OVERSTAY_HOURS || 4}h`,
    });
    s.overstayAlerted = true;
    await s.save();
  }
}
