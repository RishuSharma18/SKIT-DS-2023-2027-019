import 'dotenv/config';

const PORT = process.env.PORT || 5000;
const API_URL = process.env.SIMULATE_API_URL || `http://localhost:${PORT}/api/events`;
const API_KEY = process.env.AI_API_KEY || 'dev-key';
const DELAY_MS = 2000;
const ONCE = process.argv.includes('--once');

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

let running = true;
process.on('SIGINT', () => {
  console.log('\n[Simulate] Stopping event simulator...');
  running = false;
  process.exit(0);
});

async function sendEvent(event) {
  const timestamp = new Date().toLocaleTimeString();
  try {
    const res = await fetch(API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': API_KEY,
      },
      body: JSON.stringify(event),
    });

    const data = await res.json().catch(() => ({}));
    if (res.ok) {
      console.log(`[${timestamp}] Sent ${event.type.padEnd(14)} -> ${res.status} OK:`, JSON.stringify(event));
      return data;
    } else {
      console.error(`[${timestamp}] Error sending ${event.type} (${res.status}):`, data.error || data);
      return null;
    }
  } catch (err) {
    console.error(`[${timestamp}] Failed to reach backend at ${API_URL}: ${err.message}`);
    return null;
  }
}

async function runSimulation() {
  console.log('=====================================================');
  console.log('       Smart CCTV Parking - Event Simulator          ');
  console.log('=====================================================');
  console.log(`Target URL : ${API_URL}`);
  console.log(`API Key    : ${API_KEY}`);
  console.log(`Interval   : ${DELAY_MS / 1000}s per event`);
  console.log(`Mode       : ${ONCE ? 'Single Run (--once)' : 'Continuous Loop (Ctrl+C to stop)'}`);
  console.log('=====================================================\n');

  let cycle = 1;

  while (running) {
    const baseTrack = cycle * 100;
    const trackNormal = baseTrack + 1;
    const trackStolen = baseTrack + 2;
    const trackWrong = baseTrack + 3;

    console.log(`--- [Cycle ${cycle}] Starting simulation sequence ---`);

    // 1. Normal vehicle lifecycle (entry -> plate -> parked)
    console.log(`\n> [Normal Vehicle] Track #${trackNormal} entering`);
    await sendEvent({
      type: 'entry',
      trackId: trackNormal,
      vehicleType: 'car',
      cameraId: 'cam-1',
    });
    if (!running) break;
    await sleep(DELAY_MS);

    console.log(`> [Normal Vehicle] Detecting license plate for Track #${trackNormal}`);
    await sendEvent({
      type: 'plate',
      trackId: trackNormal,
      plate: `DL0${cycle % 9 + 1}AB${1000 + (cycle % 9000)}`,
      cameraId: 'cam-1',
    });
    if (!running) break;
    await sleep(DELAY_MS);

    console.log(`> [Normal Vehicle] Track #${trackNormal} parked in slot A-04`);
    await sendEvent({
      type: 'parked',
      trackId: trackNormal,
      slotId: 'A-04',
      cameraId: 'cam-1',
    });
    if (!running) break;
    await sleep(DELAY_MS);

    // 2. Stolen plate vehicle arrives (RJ14AB1234 is on the watchlist)
    console.log(`\n> [Stolen Vehicle] Track #${trackStolen} entering`);
    await sendEvent({
      type: 'entry',
      trackId: trackStolen,
      vehicleType: 'suv',
      cameraId: 'cam-1',
    });
    if (!running) break;
    await sleep(DELAY_MS);

    console.log(`> [Stolen Vehicle] Plate identified as RJ14AB1234 (Watchlist match)`);
    await sendEvent({
      type: 'plate',
      trackId: trackStolen,
      plate: 'RJ14AB1234',
      cameraId: 'cam-1',
    });
    if (!running) break;
    await sleep(DELAY_MS);

    console.log(`> [Stolen Vehicle] Track #${trackStolen} parked in slot A-10`);
    await sendEvent({
      type: 'parked',
      trackId: trackStolen,
      slotId: 'A-10',
      cameraId: 'cam-1',
    });
    if (!running) break;
    await sleep(DELAY_MS);

    // 3. Wrong parking event
    console.log(`\n> [Incident] Wrong parking detected`);
    await sendEvent({
      type: 'wrong_parking',
      trackId: trackWrong,
      plate: `HR26DK${2000 + cycle}`,
      slotId: 'A-01',
      cameraId: 'cam-1',
      message: 'Vehicle parked outside valid slot boundaries / blocking lane',
    });
    if (!running) break;
    await sleep(DELAY_MS);

    // 4. Crash event
    console.log(`\n> [Incident] Collision detected`);
    await sendEvent({
      type: 'crash',
      cameraId: 'cam-1',
      message: 'Collision detected near aisle junction',
    });
    if (!running) break;
    await sleep(DELAY_MS);

    // 5. Vehicles exit
    console.log(`\n> [Vehicle Exit] Track #${trackNormal} exiting`);
    await sendEvent({
      type: 'exit',
      trackId: trackNormal,
      cameraId: 'cam-1',
    });
    if (!running) break;
    await sleep(DELAY_MS);

    console.log(`> [Vehicle Exit] Track #${trackStolen} exiting`);
    await sendEvent({
      type: 'exit',
      trackId: trackStolen,
      cameraId: 'cam-1',
    });
    if (!running) break;

    console.log(`\n--- [Cycle ${cycle}] Sequence completed ---\n`);

    if (ONCE) {
      break;
    }

    cycle++;
    await sleep(DELAY_MS);
  }

  console.log('[Simulate] Finished simulation.');
}

runSimulation();
