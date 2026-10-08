export default function SlotGrid({ slots }) {
  if (!slots.length) return <p className="muted">No slots yet. Run <code>npm run seed</code> in backend.</p>;
  return (
    <div className="grid">
      {slots.map((s) => (
        <div key={s.slotId} className={`slot ${s.status}`}>
          <b>{s.slotId}</b>
          <small>{s.type}</small>
          <small>{s.status}</small>
        </div>
      ))}
    </div>
  );
}
