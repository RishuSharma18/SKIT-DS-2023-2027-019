import { useState } from 'react';

const LABEL = {
  stolen_vehicle: 'Stolen vehicle',
  crash: 'Crash',
  wrong_parking: 'Wrong parking',
  overstay: 'Overstay',
};

export default function AlertList({ alerts, onAck }) {
  const [type, setType] = useState('all');
  const filteredAlerts = type === 'all' ? alerts : alerts.filter((a) => a.type === type);

  return (
    <>
      <label className="field">
        Filter by type
        <select value={type} onChange={(event) => setType(event.target.value)}>
          <option value="all">All alerts</option>
          {Object.entries(LABEL).map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
      </label>
      {filteredAlerts.length ? (
        <ul className="alerts">
          {filteredAlerts.map((a) => (
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
      ) : <p className="muted">{alerts.length ? 'No alerts match this type.' : 'No alerts.'}</p>}
    </>
  );
}
