import { useEffect, useState } from 'react';
import { recommendSlot } from '../api.js';

export default function SlotRecommend() {
  const [type, setType] = useState('car');
  const [slot, setSlot] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let current = true;
    setLoading(true);
    setError('');
    recommendSlot(type)
      .then((result) => {
        if (current) setSlot(result.slot);
      })
      .catch((err) => {
        if (current) setError(err.message);
      })
      .finally(() => {
        if (current) setLoading(false);
      });
    return () => { current = false; };
  }, [type]);

  return (
    <>
      <h2>Slot recommendation</h2>
      <label className="field">
        Vehicle type
        <select value={type} onChange={(event) => setType(event.target.value)}>
          <option value="bike">Bike</option>
          <option value="car">Car</option>
          <option value="suv">SUV</option>
        </select>
      </label>
      {loading ? <p className="muted">Finding a free slot...</p>
        : error ? <p className="error" role="alert">{error}</p>
          : slot ? (
            <div className="recommendation">
              <span className="muted">Suggested slot</span>
              <strong>{slot.slotId}</strong>
              <span className="muted">{slot.type} - {slot.zone || 'Zone not specified'}</span>
            </div>
          ) : <p className="muted">No free slot available for this vehicle type.</p>}
    </>
  );
}
