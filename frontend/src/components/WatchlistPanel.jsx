import { useEffect, useState } from 'react';
import { addWatchlistEntry, deleteWatchlistEntry, getWatchlist } from '../api.js';

export default function WatchlistPanel() {
  const [entries, setEntries] = useState([]);
  const [plate, setPlate] = useState('');
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deletingId, setDeletingId] = useState('');
  const [loadAttempt, setLoadAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    getWatchlist()
      .then((result) => { if (active) setEntries(result); })
      .catch((requestError) => { if (active) setError(requestError.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [loadAttempt]);

  const onSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setSaving(true);
    try {
      const entryData = { plate: plate.trim().toUpperCase() };
      if (reason.trim()) entryData.reason = reason.trim();
      const entry = await addWatchlistEntry(entryData);
      setEntries((current) => [entry, ...current.filter((item) => item._id !== entry._id)]);
      setPlate('');
      setReason('');
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSaving(false);
    }
  };

  const onDelete = async (id) => {
    setError('');
    setDeletingId(id);
    try {
      await deleteWatchlistEntry(id);
      setEntries((current) => current.filter((entry) => entry._id !== id));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setDeletingId('');
    }
  };

  return (
    <>
      <div className="watchlist-intro"><span className="security-icon" aria-hidden="true">⌑</span><p>Add a vehicle plate to flag it for operator attention.</p></div>
      <form className="watchlist-form" onSubmit={onSubmit}>
        <label className="field">
          <span>Plate number</span>
          <input value={plate} onChange={(event) => setPlate(event.target.value)} placeholder="e.g. RJ14AB1234" autoComplete="off" maxLength={16} required />
        </label>
        <label className="field">
          <span>Reason <small>(optional)</small></span>
          <input value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Reported stolen" maxLength={120} />
        </label>
        <button className="button-primary add-plate-button" type="submit" disabled={saving || !plate.trim()}>
          <span aria-hidden="true">+</span> {saving ? 'Adding…' : 'Add vehicle'}
        </button>
      </form>
      {error && entries.length > 0 && <p className="error watchlist-error" role="alert">{error} <button className="text-button" onClick={() => setLoadAttempt((current) => current + 1)}>Retry</button></p>}
      <div className="watchlist-list-heading"><span>FLAGGED VEHICLES</span><span className="watchlist-count">{loading ? '…' : error && !entries.length ? '—' : entries.length}</span></div>
      {loading ? (
        <div className="panel-state watchlist-load-state" role="status"><span className="loading-spinner" aria-hidden="true" />Loading watchlist…</div>
      ) : error && !entries.length ? (
        <div className="panel-state panel-error" role="alert"><span>{error}</span><button className="text-button" onClick={() => setLoadAttempt((current) => current + 1)}>Try again</button></div>
      ) : entries.length ? (
        <ul className="watchlist">
          {entries.map((entry) => (
            <li key={entry._id}>
              <span className="plate-icon" aria-hidden="true">▰</span>
              <div className="watchlist-details">
                <code>{entry.plate}</code>
                <span>{entry.reason || 'Reported stolen'}</span>
              </div>
              <button className="remove-button" type="button" onClick={() => onDelete(entry._id)} disabled={deletingId === entry._id} aria-label={`Remove ${entry.plate} from watchlist`}>
                {deletingId === entry._id ? 'Removing…' : 'Remove'}
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <div className="empty-state watchlist-empty"><span className="empty-icon" aria-hidden="true">☆</span><b>No flagged vehicles</b><span>Added plates will be monitored by the system.</span></div>
      )}
    </>
  );
}
