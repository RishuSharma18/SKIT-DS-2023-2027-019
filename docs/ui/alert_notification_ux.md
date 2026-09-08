# Alert Notification UX & Audio Buzzer Specifications

Operator notification design for high-priority safety incidents.

## Severity Hierarchy
1. **`HIGH` Severity (`STOLEN_VEHICLE`, `ACCIDENT`)**:
   - Flashing red banner with pulse animation.
   - Distinct double-beep buzzer tone (Web Audio API synthesised at 880Hz).
   - Snapshot modal preview auto-opens with 'Acknowledge' button.

2. **`MEDIUM` Severity (`WRONG_PARKING`, `OVERSTAY`)**:
   - Amber toast notification.
   - Soft single alert chime (440Hz).
   - Dismissible via operator action.
