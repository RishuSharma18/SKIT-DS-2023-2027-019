const STATUS_COPY = {
  loading: 'Checking',
  online: 'Online',
  offline: 'Offline',
  outdated: 'Restart required',
};

function ServiceItem({ label, status, detail, error }) {
  return (
    <div className={`service-item service-${status}`} title={`${label}: ${error || detail || STATUS_COPY[status]}`}>
      <span className="service-indicator" aria-hidden="true" />
      <span className="service-label">{label}</span>
      <b>{detail || STATUS_COPY[status]}</b>
    </div>
  );
}

export default function ServiceHealth({ backend, ai, socket, camera }) {
  const aiOnline = ai.status === 'online';
  const sourceDetail = ai.sourceMode === 'video'
    ? 'Video replay'
    : ai.sourceMode === 'webcam'
      ? 'Webcam'
      : ai.sourceMode === 'network'
        ? 'IP camera'
        : ai.slotConfigError
          ? 'Map unavailable'
          : STATUS_COPY[ai.status];
  const mlDetail = aiOnline
    ? ai.durationModelAvailable
      ? ai.durationModelMetrics?.testMaeMin !== undefined
        ? `Ready · ${ai.durationModelMetrics.testMaeMin} min MAE`
        : 'Ready'
      : 'Not trained'
    : STATUS_COPY[ai.status];
  return (
    <section className="service-strip" aria-label="Connected service status">
      <div className="service-strip-heading"><span className="service-pulse" /> SERVICE HEALTH</div>
      <ServiceItem label="Backend API" status={backend.status} detail={backend.error ? 'Unavailable' : undefined} error={backend.error} />
      <ServiceItem label="Live events" status={socket} detail={socket === 'connected' ? 'Connected' : socket === 'connecting' ? 'Connecting' : 'Disconnected'} />
      <ServiceItem label="AI service" status={ai.status} detail={ai.status === 'outdated' ? 'Restart required' : ai.error ? 'Unavailable' : undefined} error={ai.error} />
      <ServiceItem label="Camera source" status={aiOnline && ai.sourceMode !== 'video' ? 'online' : ai.status === 'loading' ? 'loading' : 'offline'} detail={sourceDetail} error={ai.slotConfigError} />
      <ServiceItem label="Mapped spaces" status={aiOnline && ai.configuredSlotIds?.length ? 'online' : ai.status === 'loading' ? 'loading' : 'offline'} detail={aiOnline ? `${ai.configuredSlotIds?.length || 0} configured` : STATUS_COPY[ai.status]} />
      <ServiceItem label="Video stream" status={camera === 'loading' ? 'loading' : camera === 'online' ? 'online' : 'offline'} detail={camera === 'online' ? 'Connected' : undefined} />
      <ServiceItem label="Detection" status={aiOnline ? 'online' : ai.status} detail={aiOnline ? `${ai.inferenceImageSize}px · ${ai.tiledInference ? 'overlap tiles on high-res' : 'full frame'} · conf ${ai.confidence}` : STATUS_COPY[ai.status]} />
      <ServiceItem label="Plate OCR" status={aiOnline ? (ai.ocrEnabled ? 'online' : 'offline') : ai.status} detail={aiOnline ? (ai.ocrEnabled ? 'Enabled' : 'Disabled') : STATUS_COPY[ai.status]} />
      <ServiceItem label="Duration model" status={aiOnline ? (ai.durationModelAvailable ? 'online' : 'offline') : ai.status} detail={mlDetail} />
    </section>
  );
}
