import type {
  AlertType,
  AllocationResult,
  ApiHealth,
  ConnectionState,
  LiveEvent,
  ParkingSession,
  ParkingSlot,
  SecurityAlert,
  SlotStatus,
  VehicleCategory,
  WatchlistEntry,
} from '../types';

const API_URL = (import.meta.env.NEXT_PUBLIC_API_URL || '').replace(/\/+$/, '');
const WS_URL = import.meta.env.NEXT_PUBLIC_WS_URL?.trim();
const AI_STREAM_URL = import.meta.env.NEXT_PUBLIC_AI_STREAM_URL?.trim();
const API_V1_ROOT = API_URL.endsWith('/api/v1')
  ? API_URL
  : API_URL.endsWith('/api')
    ? `${API_URL}/v1`
    : `${API_URL}/api/v1`;
const LEGACY_API_ROOT = API_URL.endsWith('/api')
  ? API_URL
  : API_URL.endsWith('/api/v1')
    ? API_URL.slice(0, -3)
    : `${API_URL}/api`;
const OVERSTAY_HOURS = Number(import.meta.env.NEXT_PUBLIC_OVERSTAY_HOURS || 4);

type Raw = Record<string, unknown>;

function isRecord(value: unknown): value is Raw {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function text(value: unknown, fallback = ''): string {
  return typeof value === 'string' && value.length ? value : fallback;
}

function numeric(value: unknown, fallback = 0): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
}

function boolean(value: unknown, fallback = false): boolean {
  return typeof value === 'boolean' ? value : fallback;
}

function unwrapList(value: unknown): unknown[] {
  if (Array.isArray(value)) return value;
  if (!isRecord(value)) return [];
  for (const key of ['data', 'items', 'results', 'slots', 'sessions', 'alerts', 'watchlist']) {
    if (Array.isArray(value[key])) return value[key] as unknown[];
  }
  return [];
}

function unwrapRecord(value: unknown): Raw {
  if (!isRecord(value)) return {};
  return isRecord(value.data) ? value.data : value;
}

function normalizeCategory(value: unknown): VehicleCategory {
  const category = text(value).toUpperCase().replace(/[\s-]+/g, '_');
  if (['BIKE', 'MOTORBIKE', 'MOTORCYCLE', 'TWO_WHEELER'].includes(category)) return 'TWO_WHEELER';
  if (['SUV', 'SEDAN', 'SUV_SEDAN'].includes(category)) return 'SUV_SEDAN';
  if (['TRUCK', 'BUS', 'HEAVY', 'HEAVY_VEHICLE'].includes(category)) return 'HEAVY_VEHICLE';
  return 'COMPACT_CAR';
}

function legacyCategory(category: VehicleCategory): string {
  switch (category) {
    case 'TWO_WHEELER': return 'bike';
    case 'SUV_SEDAN': return 'suv';
    case 'HEAVY_VEHICLE': return 'suv';
    default: return 'car';
  }
}

function normalizeSlotStatus(value: unknown): SlotStatus {
  switch (text(value).toUpperCase()) {
    case 'OCCUPIED': return 'OCCUPIED';
    case 'RESERVED': return 'RESERVED';
    case 'VIOLATION':
    case 'WRONG_PARKING': return 'VIOLATION';
    default: return 'AVAILABLE';
  }
}

function normalizeAlertType(value: unknown): AlertType {
  switch (text(value).toUpperCase()) {
    case 'STOLEN_VEHICLE': return 'STOLEN_VEHICLE';
    case 'ACCIDENT':
    case 'CRASH': return 'ACCIDENT';
    case 'WRONG_PARKING': return 'WRONG_PARKING';
    default: return 'OVERSTAY';
  }
}

export function normalizeSlot(value: unknown): ParkingSlot {
  const raw = isRecord(value) ? value : {};
  return {
    id: text(raw.slot_id ?? raw.slotId ?? raw.id, 'Unknown'),
    status: normalizeSlotStatus(raw.status),
    category: normalizeCategory(raw.vehicle_category ?? raw.vehicleCategory ?? raw.type ?? raw.category),
    cameraId: text(raw.camera_id ?? raw.cameraId, 'CAM_01'),
    zone: text(raw.zone, 'Main'),
    plateNumber: text(raw.plate_number ?? raw.plate, '') || null,
  };
}

export function normalizeSession(value: unknown): ParkingSession {
  const raw = isRecord(value) ? value : {};
  const checkIn = text(raw.check_in_time ?? raw.checkInTime ?? raw.entryTime, new Date().toISOString());
  const checkOut = text(raw.check_out_time ?? raw.checkOutTime ?? raw.exitTime) || null;
  const duration = numeric(raw.duration_seconds ?? raw.durationSeconds ?? raw.durationSec, NaN);
  const inferredValue = checkOut
    ? Math.round((Date.parse(checkOut) - Date.parse(checkIn)) / 1000)
    : NaN;
  const inferredDuration = Number.isFinite(inferredValue) ? Math.max(0, inferredValue) : null;
  const status = text(raw.status).toUpperCase();
  const overstay = boolean(raw.overstay, false)
    || (status === 'ACTIVE' && Date.now() - Date.parse(checkIn) > OVERSTAY_HOURS * 3_600_000);
  return {
    id: text(raw.id ?? raw._id ?? raw.session_id, `${raw.trackId ?? raw.track_id ?? checkIn}`),
    plateNumber: text(raw.plate_number ?? raw.plate) || null,
    category: normalizeCategory(raw.vehicle_category ?? raw.vehicleCategory ?? raw.vehicleType ?? raw.category),
    slotId: text(raw.slot_id ?? raw.slotId) || null,
    cameraId: text(raw.camera_id ?? raw.cameraId, 'CAM_01'),
    checkInTime: checkIn,
    checkOutTime: checkOut,
    durationSeconds: Number.isFinite(duration) ? duration : inferredDuration,
    status: status === 'CLOSED' || status === 'COMPLETED' ? 'CLOSED' : 'ACTIVE',
    overstay,
  };
}

function resolveAssetUrl(value: unknown): string | null {
  const source = text(value);
  if (!source) return null;
  if (/^(data:|https?:\/\/|blob:)/i.test(source)) return source;
  if (source.length > 100 && /^[A-Za-z0-9+/]+=*$/.test(source)) {
    return `data:image/jpeg;base64,${source}`;
  }
  const base = API_URL || window.location.origin;
  return new URL(source, `${base}/`).toString();
}

export function normalizeAlert(value: unknown): SecurityAlert {
  const raw = isRecord(value) ? value : {};
  const timestamp = text(raw.timestamp ?? raw.createdAt, new Date().toISOString());
  return {
    id: text(raw.id ?? raw._id ?? raw.alert_id, timestamp),
    type: normalizeAlertType(raw.alert_type ?? raw.alertType ?? raw.type),
    severity: text(raw.severity, 'MEDIUM').toUpperCase() as SecurityAlert['severity'],
    message: text(raw.message, 'An event requires operator attention.'),
    plateNumber: text(raw.plate_number ?? raw.plate) || null,
    cameraId: text(raw.camera_id ?? raw.cameraId, 'CAM_01'),
    slotId: text(raw.slot_id ?? raw.slotId) || null,
    snapshotUrl: resolveAssetUrl(raw.snapshot_url ?? raw.snapshotUrl ?? raw.snapshot),
    acknowledged: boolean(raw.acknowledged ?? raw.is_acknowledged, false),
    timestamp,
  };
}

function normalizeWatchlist(value: unknown): WatchlistEntry {
  const raw = isRecord(value) ? value : {};
  return {
    id: text(raw.id ?? raw._id, text(raw.plate_number ?? raw.plate)),
    plateNumber: text(raw.plate_number ?? raw.plate).toUpperCase(),
    reason: text(raw.reason, 'Flagged vehicle'),
    active: boolean(raw.active ?? raw.is_active, true),
    createdAt: text(raw.created_at ?? raw.createdAt, new Date().toISOString()),
  };
}

function apiRoots(path: string): string[] {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  const primaryRoot = API_V1_ROOT;
  const legacyRoot = LEGACY_API_ROOT;
  const primary = `${primaryRoot}${normalizedPath}`;
  const legacy = `${legacyRoot}${normalizedPath}`;
  return primary === legacy ? [primary] : [primary, legacy];
}

async function requestJson(path: string, init?: RequestInit): Promise<unknown> {
  const paths = apiRoots(path);
  let latestError = new Error('The backend could not be reached.');
  for (const [index, url] of paths.entries()) {
    let response: Response;
    try {
      response = await fetch(url, {
        ...init,
        headers: { Accept: 'application/json', ...init?.headers },
      });
    } catch (error) {
      latestError = error instanceof Error ? error : latestError;
      if (index < paths.length - 1) continue;
      throw latestError;
    }

    if (response.status === 404 && index < paths.length - 1) continue;
    if (!response.ok) {
      const body: unknown = await response.json().catch(() => ({}));
      const record = isRecord(body) ? body : {};
      const detail = record.detail ?? record.error ?? record.message;
      throw new Error(typeof detail === 'string' ? detail : `Request failed (${response.status})`);
    }
    if (response.status === 204) return null;
    return response.json();
  }
  throw latestError;
}

export async function getSlots(): Promise<ParkingSlot[]> {
  return unwrapList(await requestJson('/slots')).map(normalizeSlot);
}

export async function getSessions(): Promise<ParkingSession[]> {
  return unwrapList(await requestJson('/sessions')).map(normalizeSession);
}

export async function getAlerts(): Promise<SecurityAlert[]> {
  return unwrapList(await requestJson('/alerts')).map(normalizeAlert);
}

export async function getWatchlist(): Promise<WatchlistEntry[]> {
  return unwrapList(await requestJson('/watchlist')).map(normalizeWatchlist);
}

export async function getHealth(): Promise<ApiHealth> {
  const health = unwrapRecord(await requestJson('/health'));
  return { ok: health.ok === true };
}

export async function allocateSlot(category: VehicleCategory): Promise<AllocationResult> {
  const response = unwrapRecord(await requestJson('/slots/allocate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ vehicle_category: category, vehicleType: legacyCategory(category) }),
  }));
  const slot = response.slot ?? response.recommended_slot ?? response.recommendedSlot;
  return { slot: slot ? normalizeSlot(slot) : null };
}

export async function acknowledgeAlert(id: string): Promise<SecurityAlert> {
  const response = await requestJson(`/alerts/${encodeURIComponent(id)}/ack`, { method: 'PATCH' });
  return normalizeAlert(response);
}

export interface WatchlistInput {
  plateNumber: string;
  reason: string;
  active: boolean;
}

function watchlistPayload(input: WatchlistInput): string {
  return JSON.stringify({
    plate_number: input.plateNumber.trim().toUpperCase(),
    plate: input.plateNumber.trim().toUpperCase(),
    reason: input.reason.trim(),
    active: input.active,
  });
}

export async function createWatchlistEntry(input: WatchlistInput): Promise<WatchlistEntry> {
  const response = await requestJson('/watchlist', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: watchlistPayload(input),
  });
  return normalizeWatchlist(response);
}

export async function updateWatchlistEntry(
  id: string,
  input: WatchlistInput,
): Promise<WatchlistEntry> {
  const response = await requestJson(`/watchlist/${encodeURIComponent(id)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: watchlistPayload(input),
  });
  return normalizeWatchlist(response);
}

export async function removeWatchlistEntry(id: string): Promise<void> {
  await requestJson(`/watchlist/${encodeURIComponent(id)}`, { method: 'DELETE' });
}

export function getCameraIds(): string[] {
  const configured = import.meta.env.NEXT_PUBLIC_CAMERA_IDS
    ?.split(',')
    .map((cameraId) => cameraId.trim())
    .filter(Boolean);
  return configured?.length ? configured : ['cam-1'];
}

export function getCameraStreamUrl(cameraId: string): string {
  if (AI_STREAM_URL?.includes('{camera_id}')) {
    return AI_STREAM_URL.replaceAll('{camera_id}', encodeURIComponent(cameraId));
  }
  if (AI_STREAM_URL) {
    return `${AI_STREAM_URL.replace(/\/+$/, '')}/video_feed/${encodeURIComponent(cameraId)}`;
  }
  return `/ai/stream?camera_id=${encodeURIComponent(cameraId)}`;
}

export function resolveCameraStreamFallback(cameraId: string): string {
  return `/ai/stream?camera_id=${encodeURIComponent(cameraId)}`;
}

function normalizeLiveEvent(name: string, payload: unknown): LiveEvent {
  if (typeof payload === 'string') {
    try {
      return normalizeLiveEvent(name, JSON.parse(payload) as unknown);
    } catch {
      return { name, payload };
    }
  }
  if (!isRecord(payload)) return { name, payload };
  const eventName = name === 'message'
    ? text(payload.event_type ?? payload.eventType ?? payload.type, name)
    : name;
  const eventPayload = isRecord(payload.payload) ? payload.payload : payload;
  return { name: eventName, payload: eventPayload };
}

export function connectLiveEvents(
  onEvent: (event: LiveEvent) => void,
  onStatus: (status: ConnectionState) => void,
): () => void {
  return connectNativeWebSocket(resolveWebSocketUrl(), onEvent, onStatus);
}

function resolveWebSocketUrl(): string {
  const defaultUrl = API_URL
    ? new URL('/ws/events', API_URL).toString()
    : `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/events`;
  const url = new URL(WS_URL || defaultUrl, window.location.href);
  if (url.protocol === 'http:') url.protocol = 'ws:';
  if (url.protocol === 'https:') url.protocol = 'wss:';
  if (url.pathname === '/' || !url.pathname) url.pathname = '/ws/events';
  return url.toString();
}

function connectNativeWebSocket(
  url: string,
  onEvent: (event: LiveEvent) => void,
  onStatus: (status: ConnectionState) => void,
): () => void {
  let socket: WebSocket | null = null;
  let retryTimer: number | undefined;
  let retryDelay = 500;
  let stopped = false;

  const connect = () => {
    if (stopped) return;
    onStatus('connecting');
    try {
      socket = new WebSocket(url);
    } catch {
      onStatus('disconnected');
      scheduleReconnect();
      return;
    }

    socket.onopen = () => {
      retryDelay = 500;
      onStatus('connected');
    };
    socket.onmessage = (message) => {
      onEvent(normalizeLiveEvent('message', message.data as unknown));
    };
    socket.onerror = () => socket?.close();
    socket.onclose = () => {
      onStatus('disconnected');
      scheduleReconnect();
    };
  };

  const scheduleReconnect = () => {
    if (stopped || retryTimer !== undefined) return;
    const jitter = Math.random() * retryDelay * 0.2;
    retryTimer = window.setTimeout(() => {
      retryTimer = undefined;
      connect();
    }, retryDelay + jitter);
    retryDelay = Math.min(30_000, Math.round(retryDelay * 1.8));
  };

  connect();
  return () => {
    stopped = true;
    if (retryTimer !== undefined) window.clearTimeout(retryTimer);
    socket?.close();
  };
}
