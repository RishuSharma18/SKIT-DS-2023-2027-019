import { useEffect, useState } from 'react';
import { addWatchlistEntry, deleteWatchlistEntry, getWatchlist } from '../api.js';

export default function WatchlistPanel() {
  const [entries, setEntries] = useState([]);
  const [plate, setPlate] = useState('');
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getWatchlist()
      .then(setEntries)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const onSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setSaving(true);
    try {
      const entryData = { plate: plate.trim() };
      if (reason.trim()) entryData.reason = reason.trim();
      const entry = await addWatchlistEntry(entryData);
      setEntries((current) => [entry, ...current]);
      setPlate('');
      setReason('');
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const onDelete = async (id) => {
    setError('');
    try {
      await deleteWatchlistEntry(id);
      setEntries((current) => current.filter((entry) => entry._id !== id));
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <>
      <h2>Vehicle watchlist</h2>
      <form className="watchlist-form" onSubmit={onSubmit}>
        <label className="field">
          Plate number
          <input
            value={plate}
            onChange={(event) => setPlate(event.target.value)}
            placeholder="RJ14AB1234"
            required
          />
        </label>
        <label className="field">
          Reason <span className="muted">(optional)</span>
          <input
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            placeholder="Reported stolen"
          />
        </label>
        <button type="submit" disabled={saving}>{saving ? 'Adding...' : 'Add plate'}</button>
      </form>
      {error && <p className="error" role="alert">{error}</p>}
      {loading ? <p className="muted">Loading watchlist...</p> : entries.length ? (
        <ul className="watchlist">
          {entries.map((entry) => (
            <li key={entry._id}>
              <div>
                <code>{entry.plate}</code>
                <div className="muted">{entry.reason}</div>
              </div>
              <button className="button-secondary" onClick={() => onDelete(entry._id)}>
                Delete
              </button>
            </li>
          ))}
        </ul>
      ) : <p className="muted">No watchlist entries.</p>}
    </>
  );
}
