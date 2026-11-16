const formatHour = (hour) => `${String(hour).padStart(2, '0')}:00`;

export default function HourlyTraffic({ data }) {
  const maxEntries = Math.max(1, ...data.map((point) => point.entries));
  const peak = data.reduce((highest, point) => point.entries > highest.entries ? point : highest, data[0] || { hour: 0, entries: 0 });

  return (
    <div className="traffic-content">
      <div className="traffic-summary">
        <span><b>{data.reduce((sum, point) => sum + point.entries, 0)}</b> entries today</span>
        <span>Peak hour <b>{peak.entries ? formatHour(peak.hour) : '—'}</b></span>
      </div>
      <div className="traffic-chart" role="img" aria-label={`Hourly vehicle arrivals. ${data.map((point) => `${formatHour(point.hour)}: ${point.entries}`).join(', ')}`}>
        {data.map((point) => (
          <div className={`traffic-column ${point.hour === peak.hour && point.entries ? 'peak' : ''}`} key={point.hour} title={`${formatHour(point.hour)} · ${point.entries} ${point.entries === 1 ? 'entry' : 'entries'}`}>
            <div className="traffic-bar-track"><span style={{ height: `${point.entries ? Math.max(8, point.entries / maxEntries * 100) : 0}%` }} /></div>
            <small>{point.hour % 3 === 0 ? `${String(point.hour).padStart(2, '0')}` : ''}</small>
          </div>
        ))}
      </div>
      <div className="traffic-axis"><span>12 AM</span><span>6 AM</span><span>12 PM</span><span>6 PM</span><span>11 PM</span></div>
    </div>
  );
}
