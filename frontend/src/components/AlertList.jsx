const LABEL = {
  stolen_vehicle: 'Stolen vehicle',
  crash: 'Crash',
  wrong_parking: 'Wrong parking',
  overstay: 'Overstay',
};

export default function AlertList({ alerts, onAck }) {
  if (!alerts.length) return <p className="muted">No alerts.</p>;
  return (
    <ul className="alerts">
      {alerts.map((a) => (
        <li key={a._id} className={`sev-${a.severity} ${a.acknowledged ? 'done' : ''}`}>
          <div>
            <b>{LABEL[a.type] || a.type}</b> {a.plate && <code>{a.plate}</code>}
            <div className="muted">{a.message}</div>
            <small className="muted">{new Date(a.createdAt).toLocaleString()}</small>
          </div>
          {!a.acknowledged && <button onClick={() => onAck(a._id)}>Acknowledge</button>}
        </li>
      ))}
    </ul>
  );
}
