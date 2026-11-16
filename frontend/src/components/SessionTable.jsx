import { useState } from 'react';

const formatDuration = (seconds) => {
  if (!Number.isFinite(seconds)) return '—';
  const totalMinutes = Math.floor(seconds / 60);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return hours ? `${hours}h ${minutes}m` : `${minutes}m`;
};

const formatTime = (value) => {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
};

export default function SessionTable({ sessions }) {
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('all');
  const filteredSessions = sessions.filter((session) => {
    const matchesStatus = status === 'all' || session.status === status;
    const searchText = `${session.plate || ''} ${session.slotId || ''} ${session.vehicleType || ''}`.toLowerCase();
    return matchesStatus && searchText.includes(query.trim().toLowerCase());
  });

  return (
    <>
      <div className="activity-controls">
        <label className="search-field">
          <span aria-hidden="true">⌕</span>
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search plate, slot or vehicle" aria-label="Search activity" />
        </label>
        <label className="sr-only" htmlFor="session-status">Filter activity by status</label>
        <select id="session-status" value={status} onChange={(event) => setStatus(event.target.value)}>
          <option value="all">All activity</option><option value="active">Currently parked</option><option value="closed">Completed</option>
        </select>
      </div>
      {filteredSessions.length ? (
        <div className="scroll">
          <table>
            <thead><tr><th>VEHICLE</th><th>TYPE</th><th>SPACE</th><th>CHECKED IN</th><th>CHECKED OUT</th><th>DURATION</th><th>STATUS</th></tr></thead>
            <tbody>
              {filteredSessions.map((session) => (
                <tr key={session._id}>
                  <td><span className="session-plate">{session.plate || 'Plate pending'}</span><small className="session-id">Track #{session.trackId ?? '—'}</small></td>
                  <td><span className="type-tag">{session.vehicleType || 'Unknown'}</span></td>
                  <td>{session.slotId || '—'}</td>
                  <td>{formatTime(session.entryTime)}</td>
                  <td>{formatTime(session.exitTime)}</td>
                  <td>{session.status === 'closed' ? formatDuration(session.durationSec) : 'In progress'}</td>
                  <td><span className={`session-status ${session.status === 'active' ? 'is-active' : 'is-closed'}`}><i />{session.status === 'active' ? 'Parked' : 'Completed'}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty-state activity-empty"><span className="empty-icon" aria-hidden="true">↗</span><b>{sessions.length ? 'No matching activity' : 'No vehicle activity yet'}</b><span>{sessions.length ? 'Try another search or status filter.' : 'Check-ins and check-outs will appear here.'}</span></div>
      )}
      <div className="activity-footer"><span>Showing {filteredSessions.length} of {sessions.length} records</span><span>Updates automatically when connected</span></div>
    </>
  );
}
