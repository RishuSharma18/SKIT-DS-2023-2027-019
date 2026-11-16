const STATUS_LABELS = { free: 'Available', occupied: 'Occupied', reserved: 'Reserved' };

export default function SlotGrid({ slots }) {
  if (!slots.length) {
    return <div className="empty-state slot-empty"><span className="empty-icon" aria-hidden="true">⌖</span><b>No parking spaces yet</b><span>Seed the backend to add facility spaces.</span></div>;
  }

  return (
    <div className="grid" aria-label="Parking space status">
      {slots.map((slot) => {
        const status = STATUS_LABELS[slot.status] ? slot.status : 'reserved';
        return (
          <div key={slot.slotId} className={`slot ${status}`} title={`${slot.slotId}: ${STATUS_LABELS[status]}`}>
            <span className="slot-status-mark" aria-hidden="true">{status === 'free' ? '✓' : status === 'occupied' ? '●' : '◆'}</span>
            <b>{slot.slotId}</b>
            <small>{slot.type}</small>
            <span className="slot-status-label">{STATUS_LABELS[status]}</span>
          </div>
        );
      })}
    </div>
  );
}
