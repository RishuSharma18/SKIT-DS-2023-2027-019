const fmtDur = (s) => `${Math.floor(s / 60)}m ${s % 60}s`;

export default function SessionTable({ sessions }) {
  if (!sessions.length) return <p className="muted">No vehicles recorded yet.</p>;
  return (
    <div className="scroll">
      <table>
        <thead>
          <tr><th>Plate</th><th>Type</th><th>Slot</th><th>Entry</th><th>Exit</th><th>Duration</th><th>Status</th></tr>
        </thead>
        <tbody>
          {sessions.map((s) => (
            <tr key={s._id}>
              <td>{s.plate || '—'}</td>
              <td>{s.vehicleType}</td>
              <td>{s.slotId || '—'}</td>
              <td>{new Date(s.entryTime).toLocaleTimeString()}</td>
              <td>{s.exitTime ? new Date(s.exitTime).toLocaleTimeString() : '—'}</td>
              <td>{s.status === 'closed' ? fmtDur(s.durationSec) : 'in progress'}</td>
              <td>{s.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
