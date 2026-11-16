import { useEffect, useState } from 'react';
import { predictDuration, recommendSlot } from '../api.js';

const VEHICLES = [
  { value: 'bike', label: 'Motorcycle', icon: '◈' },
  { value: 'car', label: 'Car', icon: '▰' },
  { value: 'suv', label: 'SUV', icon: '▰' },
];

export default function SlotRecommend() {
  const [type, setType] = useState('car');
  const [slot, setSlot] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [duration, setDuration] = useState(null);
  const [durationLoading, setDurationLoading] = useState(true);
  const [durationError, setDurationError] = useState('');
  const [retry, setRetry] = useState(0);
  const selectedVehicle = VEHICLES.find((vehicle) => vehicle.value === type);

  useEffect(() => {
    let current = true;
    setLoading(true);
    setError('');
    setDurationLoading(true);
    setDurationError('');
    const now = new Date();
    const weekday = (now.getDay() + 6) % 7;

    Promise.allSettled([
      recommendSlot(type),
      predictDuration({ vehicleType: type, arrivalHour: now.getHours(), weekday }),
    ]).then(([recommendationResult, durationResult]) => {
      if (!current) return;
      if (recommendationResult.status === 'fulfilled') {
        setSlot(recommendationResult.value.slot);
      } else {
        setSlot(null);
        setError(recommendationResult.reason.message);
      }

      if (durationResult.status === 'fulfilled') {
        setDuration(durationResult.value.estimatedDurationMin);
      } else {
        setDuration(null);
        setDurationError(durationResult.reason.message);
      }
      setLoading(false);
      setDurationLoading(false);
    });
    return () => { current = false; };
  }, [type, retry]);

  return (
    <>
      <div className="panel-heading">
        <div><p className="eyebrow">SMART ALLOCATION</p><h2>Find the right space</h2></div>
        <span className="recommend-icon" aria-hidden="true">✦</span>
      </div>
      <p className="recommend-copy">Get the best available slot based on your vehicle type.</p>
      <span className="vehicle-label">SELECT VEHICLE</span>
      <div className="vehicle-options" role="group" aria-label="Vehicle type">
        {VEHICLES.map((vehicle) => (
          <button key={vehicle.value} className={`vehicle-option ${type === vehicle.value ? 'selected' : ''}`} onClick={() => setType(vehicle.value)} aria-pressed={type === vehicle.value}>
            <span aria-hidden="true">{vehicle.icon}</span>{vehicle.label}
          </button>
        ))}
      </div>
      {loading ? (
        <div className="recommendation-state"><span className="loading-spinner" />Finding the best available space…</div>
      ) : error ? (
        <div className="recommendation-error" role="alert"><span>{error}</span><button className="text-button" onClick={() => setRetry((current) => current + 1)}>Try again</button></div>
      ) : slot ? (
        <div className="recommendation">
          <div className="recommendation-top"><span className="recommend-success"><span className="status-dot online" /> BEST MATCH</span><span className="vehicle-chip">{selectedVehicle?.label}</span></div>
          <div className="recommended-slot">{slot.slotId}</div>
          <div className="recommendation-bottom"><span>{slot.zone ? `Zone ${slot.zone}` : 'Parking zone'} <i /> {slot.type || selectedVehicle?.label}</span><span className="available-label">Available now</span></div>
        </div>
      ) : (
        <div className="recommendation-empty"><span aria-hidden="true">⌖</span><b>No matching space available</b><span>Try another vehicle type or check again later.</span></div>
      )}
      <div className="duration-estimate" aria-live="polite">
        <span className="duration-icon" aria-hidden="true">◷</span>
        <div>
          <b>{durationLoading ? 'Estimating stay…' : durationError ? 'Duration estimate unavailable' : duration ? `Estimated stay · ${duration} min` : 'No duration estimate'}</b>
          <span>{durationError ? durationError : 'Prototype estimate from synthetic data; advisory only. Slot assignment still uses current allocation rules.'}</span>
        </div>
      </div>
    </>
  );
}
