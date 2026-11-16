const formatReadTime = (value) => {
  if (!value) return 'Time unavailable';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Time unavailable' : date.toLocaleString([], { hour: '2-digit', minute: '2-digit', month: 'short', day: 'numeric' });
};

export default function PlateReads({ sessions }) {
  const reads = sessions
    .filter((session) => session.plate)
    .sort((left, right) => new Date(right.updatedAt || right.entryTime) - new Date(left.updatedAt || left.entryTime))
    .slice(0, 5);

  return reads.length ? (
    <ul className="plate-reads">
      {reads.map((session) => (
        <li key={session._id}>
          <span className="ocr-check" aria-label="Plate recognized">✓</span>
          <div className="plate-read-main"><code>{session.plate}</code><span>{session.vehicleType || 'Vehicle'}{session.cameraId ? ` · ${session.cameraId}` : ''}</span></div>
          <time dateTime={session.updatedAt || session.entryTime}>{formatReadTime(session.updatedAt || session.entryTime)}</time>
        </li>
      ))}
    </ul>
  ) : (
    <div className="empty-state ocr-empty"><span className="empty-icon" aria-hidden="true">⌕</span><b>No plates recognized yet</b><span>OCR reads appear here after a vehicle is detected.</span></div>
  );
}
