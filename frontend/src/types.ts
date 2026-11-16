export type VehicleCategory =
  | 'TWO_WHEELER'
  | 'COMPACT_CAR'
  | 'SUV_SEDAN'
  | 'HEAVY_VEHICLE';

export type SlotStatus = 'AVAILABLE' | 'OCCUPIED' | 'RESERVED' | 'VIOLATION';
export type AlertType = 'STOLEN_VEHICLE' | 'ACCIDENT' | 'WRONG_PARKING' | 'OVERSTAY';

export interface ParkingSlot {
  id: string;
  status: SlotStatus;
  category: VehicleCategory;
  cameraId: string;
  zone: string;
  plateNumber?: string | null;
}

export interface ParkingSession {
  id: string;
  plateNumber: string | null;
  category: VehicleCategory;
  slotId: string | null;
  cameraId: string;
  checkInTime: string;
  checkOutTime: string | null;
  durationSeconds: number | null;
  status: 'ACTIVE' | 'CLOSED';
  overstay: boolean;
}

export interface SecurityAlert {
  id: string;
  type: AlertType;
  severity: 'LOW' | 'MEDIUM' | 'HIGH';
  message: string;
  plateNumber: string | null;
  cameraId: string;
  slotId: string | null;
  snapshotUrl: string | null;
  acknowledged: boolean;
  timestamp: string;
}

export interface WatchlistEntry {
  id: string;
  plateNumber: string;
  reason: string;
  active: boolean;
  createdAt: string;
}

export interface AllocationResult {
  slot: ParkingSlot | null;
}

export interface LiveEvent {
  name: string;
  payload: unknown;
}

export type ConnectionState = 'connecting' | 'connected' | 'disconnected';

export interface ToastMessage {
  id: string;
  title: string;
  message: string;
  tone: 'success' | 'error' | 'warning' | 'info';
}

export interface ApiHealth {
  ok: boolean;
}
