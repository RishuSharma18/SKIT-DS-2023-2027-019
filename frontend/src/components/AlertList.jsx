import { useState } from 'react';

const LABEL = {
  stolen_vehicle: 'Stolen vehicle',
  crash: 'Crash detected',
  wrong_parking: 'Wrong parking',
  overstay: 'Overstay',
};

const formatDate = (value) => {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Time unavailable' : date.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });
};

const snapshotUrl = (snapshot) => {
  if (!snapshot) return '';
  if (/^https?:\/\//i.test(snapshot)) return snapshot;
  return snapshot.startsWith('/') ? snapshot : `/${snapshot}`;
};

export default function AlertList({ alerts, onAck }) {
  const [type, setType] = useState('all');
  const [status, setStatus] = useState('open');
  const [pendingId, setPendingId] = useState('');
  const filteredAlerts = alerts.filter((alert) => (
    (type === 'all' || alert.type === type)
    && (status === 'all' || (status === 'open' ? !alert.acknowledged : alert.acknowledged))
  ));

  const acknowledge = async (id) => {
    setPendingId(id);
    try {
      await onAck(id);
    } finally {
      setPendingId('');
    }
  };

  return (
    <>
      <div className="alert-controls">
        <label className="sr-only" htmlFor="alert-category">Filter alerts by category</label>
        <select id="alert-category" value={type} onChange={(event) => setType(event.target.value)}>
          <option value="all">All categories</option>
          {Object.entries(LABEL).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
        <div className="filter-pills" aria-label="Alert status">
          <button className={status === 'open' ? 'selected' : ''} onClick={() => setStatus('open')}>Open <span>{alerts.filter((alert) => !alert.acknowledged).length}</span></button>
          <button className={status === 'all' ? 'selected' : ''} onClick={() => setStatus('all')}>All <span>{alerts.length}</span></button>
        </div>
      </div>
      {filteredAlerts.length ? (
        <ul className="alerts">
          {filteredAlerts.map((alert) => (
            <li key={alert._id} className={`alert-item sev-${alert.severity || 'medium'} ${alert.acknowledged ? 'done' : ''}`}>
              <span className="alert-indicator" aria-hidden="true" />
              <div className="alert-content">
                <div className="alert-title-row">
                  <b>{LABEL[alert.type] || alert.type}</b>
                  <span className={`severity-badge severity-${alert.severity || 'medium'}`}>{alert.severity || 'medium'}</span>
                </div>
                <p>{alert.message || 'An event requires review.'}</p>
                <div className="alert-meta">
                  {alert.plate && <code>{alert.plate}</code>}
                  {alert.slotId && <span>Slot {alert.slotId}</span>}
                  {alert.cameraId && <span>{alert.cameraId}</span>}
                  <time dateTime={alert.createdAt}>{formatDate(alert.createdAt)}</time>
                </div>
                {alert.snapshot && (
                  <a className="alert-snapshot" href={snapshotUrl(alert.snapshot)} target="_blank" rel="noreferrer">
                    <img src={snapshotUrl(alert.snapshot)} alt={`Camera snapshot for ${LABEL[alert.type] || alert.type}`} loading="lazy" />
                    <span>View camera snapshot ↗</span>
                  </a>
                )}
              </div>
              {alert.acknowledged
                ? <span className="acknowledged-label">Acknowledged</span>
                : <button className="button-quiet ack-button" onClick={() => acknowledge(alert._id)} disabled={pendingId === alert._id}>
                  {pendingId === alert._id ? 'Saving…' : 'Acknowledge'}
                </button>}
            </li>
          ))}
        </ul>
      ) : (
        <div className="empty-state compact-empty">
          <span className="empty-icon" aria-hidden="true">{status === 'open' ? '✓' : '◌'}</span>
          <b>{alerts.length ? 'No alerts match these filters' : 'All clear'}</b>
          <span>{alerts.length ? 'Try another category or view all alerts.' : 'New safety alerts will appear here.'}</span>
        </div>
      )}
    </>
  );
}
