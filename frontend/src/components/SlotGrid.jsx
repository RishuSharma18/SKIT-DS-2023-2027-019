const STATUS_LABELS = { free: 'Available', occupied: 'Occupied', reserved: 'Reserved' };
const STATUS_MARKS = { free: '✓', occupied: '●', reserved: '◆', unknown: '?' };

export default function SlotGrid({ slots, verified = false }) {
  if (!slots.length) {
    return <div className="empty-state slot-empty"><span className="empty-icon" aria-hidden="true">⌖</span><b>No camera-mapped spaces configured</b><span>Configure parking-space polygons in the AI service camera map.</span></div>;
  }

  return (
    <div className="grid" aria-label="Parking space status">
      {slots.map((slot) => {
        const status = verified && STATUS_LABELS[slot.status] ? slot.status : 'unknown';
        const label = verified ? STATUS_LABELS[status] || 'Unknown' : 'Unverified';
        return (
          <div key={slot.slotId} className={`slot ${status}`} title={`${slot.slotId}: ${label}`}>
            <span className="slot-status-mark" aria-hidden="true">{STATUS_MARKS[status]}</span>
            <b>{slot.slotId}</b>
            <small>{slot.type}</small>
            <span className="slot-status-label">{label}</span>
          </div>
        );
      })}
    </div>
  );
}
