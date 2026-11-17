# WebSocket Client Telemetry Binding Specification

React hooks and WebSocket state binding for `/ws/events`.

## Hook API: `useRealtimeEvents`
```typescript
interface UseRealtimeEventsOptions {
  url: string;
  onSlotUpdate?: (slots: ParkingSlot[]) => void;
  onNewAlert?: (alert: Alert) => void;
  onNewSession?: (session: VehicleSession) => void;
}
```

## Reconnection Strategy
- Exponential backoff starting at 1,000ms with a cap at 30,000ms.
- Auto-ping keepalive interval: 25,000ms.
