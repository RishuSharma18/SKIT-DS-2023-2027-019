import { useCallback, useEffect, useState } from 'react';
import { ackAlert, getAiHealth, getAlerts, getBackendHealth, getHourlyAnalytics, getSessions, getSlots, getStats } from './api.js';
import AlertList from './components/AlertList.jsx';
import HourlyTraffic from './components/HourlyTraffic.jsx';
import PlateReads from './components/PlateReads.jsx';
import SessionTable from './components/SessionTable.jsx';
import ServiceHealth from './components/ServiceHealth.jsx';
import SlotGrid from './components/SlotGrid.jsx';
import SlotRecommend from './components/SlotRecommend.jsx';
import PanelState from './components/PanelState.jsx';
import WatchlistPanel from './components/WatchlistPanel.jsx';

const formatUpdated = (date) => date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
const cameraMapHealth = (health) => {
  const camera = health?.cameras?.find((item) => item.cameraId === health.cameraId)
    || health?.cameras?.[0]
    || health;
  if (typeof camera?.cameraId !== 'string'
      || !camera.cameraId.trim()
      || !['video', 'webcam', 'network'].includes(camera.sourceMode)
      || !Array.isArray(camera.configuredSlotIds)
      || !Array.isArray(camera.configuredSlots)) return null;
  const slotIds = camera.configuredSlots.map((slot) => slot?.slotId);
  if (slotIds.length !== camera.configuredSlotIds.length
      || !camera.configuredSlotIds.every((slotId) => slotIds.includes(slotId))) return null;
  return { ...health, ...camera };
};
const INITIAL_PANEL_STATES = {
  slots: { loading: true, error: '' },
  alerts: { loading: true, error: '' },
  sessions: { loading: true, error: '' },
  stats: { loading: true, error: '' },
  analytics: { loading: true, error: '' },
};

export default function App() {
  const [slots, setSlots] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [stats, setStats] = useState(null);
  const [hourly, setHourly] = useState([]);
  const [loading, setLoading] = useState(true);
  const [panelStates, setPanelStates] = useState(INITIAL_PANEL_STATES);
  const [actionError, setActionError] = useState('');
  const [connection, setConnection] = useState('disconnected');
  const [cameraOccupancy, setCameraOccupancy] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [feedAvailable, setFeedAvailable] = useState(true);
  const [feedLoading, setFeedLoading] = useState(true);
  const [backendHealth, setBackendHealth] = useState({ status: 'loading' });
  const [aiHealth, setAiHealth] = useState({
    status: 'loading',
    ocrEnabled: false,
    durationModelAvailable: false,
    configuredSlotIds: [],
    configuredSlots: [],
  });
  const [theme, setTheme] = useState(() => {
    try {
      return window.localStorage.getItem('parkwise-theme') === 'dark' ? 'dark' : 'light';
    } catch (error) {
      console.error('Could not read the saved theme preference.', error);
      return 'light';
    }
  });

  const loadDashboard = useCallback(async (keys = ['slots', 'alerts', 'sessions', 'stats', 'analytics']) => {
    setLoading(true);
    const loaders = {
      slots: { request: getSlots, update: setSlots },
      alerts: { request: getAlerts, update: setAlerts },
      sessions: { request: getSessions, update: setSessions },
      stats: { request: getStats, update: setStats },
      analytics: { request: getHourlyAnalytics, update: setHourly },
    };
    setPanelStates((current) => ({
      ...current,
      ...Object.fromEntries(keys.map((key) => [key, { loading: true, error: '' }])),
    }));

    await Promise.all(keys.map(async (key) => {
      try {
        const data = await loaders[key].request();
        loaders[key].update(data);
        setPanelStates((current) => ({ ...current, [key]: { loading: false, error: '' } }));
      } catch (error) {
        setPanelStates((current) => ({ ...current, [key]: { loading: false, error: error.message } }));
      }
    }));

    setLastUpdated(new Date());
    setLoading(false);
  }, []);

  const refreshHealth = useCallback(async () => {
    const [backendResult, aiResult] = await Promise.allSettled([getBackendHealth(), getAiHealth()]);
    setBackendHealth(backendResult.status === 'fulfilled'
      ? { status: 'online' }
      : { status: 'offline', error: backendResult.reason.message });
    const cameraHealth = aiResult.status === 'fulfilled'
      ? cameraMapHealth(aiResult.value)
      : null;
    setAiHealth(aiResult.status === 'fulfilled' && cameraHealth
      ? {
        status: ['error', 'reconnecting'].includes(cameraHealth.status) ? 'offline' : 'online',
        error: cameraHealth.error || undefined,
        ocrEnabled: aiResult.value.ocrEnabled,
        durationModelAvailable: aiResult.value.durationModelAvailable,
        durationModelMetrics: aiResult.value.durationModelMetrics,
        cameraId: cameraHealth.cameraId,
        sourceMode: cameraHealth.sourceMode,
        configuredSlotIds: cameraHealth.configuredSlotIds,
        configuredSlots: cameraHealth.configuredSlots,
        slotConfigError: cameraHealth.error,
        inferenceImageSize: aiResult.value.inferenceImageSize,
        confidence: aiResult.value.confidence,
        tiledInference: aiResult.value.tiledInference,
      }
      : {
        status: 'offline',
        ocrEnabled: false,
        durationModelAvailable: false,
        configuredSlotIds: [],
        configuredSlots: [],
        error: aiResult.status === 'rejected'
          ? aiResult.reason.message
          : 'The AI service health response does not include a valid camera configuration.',
      });
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      window.localStorage.setItem('parkwise-theme', theme);
    } catch (error) {
      console.error('Could not save the theme preference.', error);
    }
  }, [theme]);

  useEffect(() => {
    loadDashboard();
    refreshHealth();
    const healthInterval = window.setInterval(refreshHealth, 30_000);

    let disposed = false;
    let reconnectTimer;
    let socket;
    const connect = () => {
      if (disposed) return;
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const activeSocket = new WebSocket(`${protocol}//${window.location.host}/ws/events`);
      socket = activeSocket;
      activeSocket.onopen = () => setConnection('connected');
      activeSocket.onclose = () => {
        setConnection('disconnected');
        if (!disposed) reconnectTimer = window.setTimeout(connect, 2000);
      };
      activeSocket.onerror = () => activeSocket.close();
      activeSocket.onmessage = ({ data }) => {
        let message;
        try {
          message = JSON.parse(data);
        } catch (error) {
          console.error('Could not parse a realtime event.', error);
          return;
        }
        const { event, payload } = message;
        if (event === 'camera:occupancy') {
          setCameraOccupancy({ ...payload, receivedAt: Date.now() });
        } else if (event === 'slots:update') {
          setSlots(payload);
          setPanelStates((current) => ({ ...current, slots: { loading: false, error: '' } }));
          setLastUpdated(new Date());
          loadDashboard(['stats']);
        } else if (event === 'alert:new') {
          setAlerts((current) => [payload, ...current.filter((item) => item._id !== payload._id)]);
          setPanelStates((current) => ({ ...current, alerts: { loading: false, error: '' } }));
          setLastUpdated(new Date());
          loadDashboard(['stats']);
        } else if (event === 'session:new') {
          setSessions((current) => [payload, ...current.filter((item) => item._id !== payload._id)]);
          setPanelStates((current) => ({ ...current, sessions: { loading: false, error: '' } }));
          setLastUpdated(new Date());
          loadDashboard(['stats', 'analytics']);
        } else if (event === 'session:update') {
          setSessions((current) => current.map((item) => (item._id === payload._id ? payload : item)));
          setPanelStates((current) => ({ ...current, sessions: { loading: false, error: '' } }));
          setLastUpdated(new Date());
          loadDashboard(['stats']);
        }
      };
    };
    connect();

    return () => {
      disposed = true;
      window.clearInterval(healthInterval);
      window.clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, [loadDashboard, refreshHealth]);

  const configuredSlotIds = aiHealth.configuredSlotIds || [];
  const configuredSlots = configuredSlotIds.length
    ? slots.filter((slot) => configuredSlotIds.includes(slot.slotId))
    : [];
  const open = alerts.filter((alert) => !alert.acknowledged).length;
  const slotsUnavailable = panelStates.slots.loading || Boolean(panelStates.slots.error);
  const alertsUnavailable = panelStates.alerts.loading || Boolean(panelStates.alerts.error);
  const statsUnavailable = panelStates.stats.loading || Boolean(panelStates.stats.error);
  const isVideoReplay = aiHealth.status === 'online' && aiHealth.sourceMode === 'video';
  const configuredSlotsPresent = configuredSlotIds.length > 0
    && configuredSlots.length === configuredSlotIds.length;
  const cameraMapSynced = cameraOccupancy?.cameraId === aiHealth.cameraId
    && cameraOccupancy?.sourceMode === aiHealth.sourceMode
    && configuredSlotIds.length > 0
    && Array.isArray(cameraOccupancy?.slotIds)
    && Array.isArray(cameraOccupancy?.occupiedSlotIds)
    && Array.isArray(cameraOccupancy?.slots)
    && configuredSlotIds.every((slotId) => cameraOccupancy.slotIds.includes(slotId));
  const occupancyFresh = cameraMapSynced
    && connection === 'connected'
    && Date.now() - cameraOccupancy.receivedAt < 15_000;
  const liveOccupancyVerified = aiHealth.status === 'online'
    && backendHealth.status === 'online'
    && ['webcam', 'network'].includes(aiHealth.sourceMode)
    && configuredSlotsPresent
    && occupancyFresh
    && !slotsUnavailable
    && feedAvailable
    && !feedLoading;
  const replayOccupancyAvailable = aiHealth.status === 'online'
    && backendHealth.status === 'online'
    && isVideoReplay
    && occupancyFresh
    && !slotsUnavailable
    && feedAvailable
    && !feedLoading;
  const occupancyVerified = liveOccupancyVerified || replayOccupancyAvailable;
  const detectionSummary = occupancyVerified ? cameraOccupancy?.detectionSummary : null;
  const occupiedSlotIds = new Set(cameraOccupancy?.occupiedSlotIds || []);
  const configuredSlotDefinitions = new Map(
    (aiHealth.configuredSlots || []).map((slot) => [slot.slotId, slot])
  );
  const cameraDisplaySlots = configuredSlotIds.map((slotId) => {
    const savedSlot = configuredSlots.find((slot) => slot.slotId === slotId);
    const configured = configuredSlotDefinitions.get(slotId);
    return {
      ...savedSlot,
      slotId,
      type: savedSlot?.type || configured?.type || 'car',
      status: !occupancyVerified
        ? 'unknown'
        : occupiedSlotIds.has(slotId)
          ? 'occupied'
          : savedSlot?.status === 'reserved' && liveOccupancyVerified
            ? 'reserved'
            : 'free',
    };
  });
  const free = cameraDisplaySlots.filter((slot) => slot.status === 'free').length;
  const occupied = cameraDisplaySlots.filter((slot) => slot.status === 'occupied').length;
  const summaryOpen = liveOccupancyVerified
    ? (statsUnavailable ? open : stats?.openAlerts ?? open)
    : 0;
  const cameraSourceLabel = isVideoReplay
    ? 'VIDEO REPLAY'
    : aiHealth.sourceMode === 'webcam'
      ? 'WEBCAM'
      : aiHealth.sourceMode === 'network'
        ? 'IP CAMERA'
        : 'CAMERA';

  const onAck = async (id) => {
    setActionError('');
    try {
      const updated = await ackAlert(id);
      setAlerts((current) => current.map((alert) => (alert._id === id ? updated : alert)));
      return true;
    } catch (error) {
      setActionError(error.message);
      return false;
    }
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#overview" aria-label="Parkwise dashboard home">
          <span className="brand-mark" aria-hidden="true">P</span>
          <span>parkwise<span className="brand-period">.</span><small>SMART PARKING</small></span>
        </a>
        <div className="sidebar-label">WORKSPACE</div>
        <nav className="side-nav" aria-label="Dashboard sections">
          <a className="side-link active" href="#overview"><span aria-hidden="true">▦</span> Overview</a>
          <a className="side-link" href="#parking"><span aria-hidden="true">⌖</span> Parking</a>
          <a className="side-link" href="#alerts"><span aria-hidden="true">◉</span> Alerts{summaryOpen > 0 && <span className="nav-count">{summaryOpen}</span>}</a>
          <a className="side-link" href="#watchlist"><span aria-hidden="true">☆</span> Watchlist</a>
          <a className="side-link" href="#activity"><span aria-hidden="true">↗</span> Activity</a>
        </nav>
        <div className="sidebar-bottom">
          <div className="system-card">
            <span className={`status-dot ${connection === 'connected' && !isVideoReplay ? 'online' : ''}`} />
            <div><b>System status</b><span>{isVideoReplay ? 'Video replay mode' : connection === 'connected' ? 'All systems operational' : connection === 'connecting' ? 'Connecting to server…' : 'Live updates unavailable'}</span></div>
          </div>
          <div className="sidebar-foot">PARKING OPERATIONS <span>v1.0</span></div>
        </div>
      </aside>

      <div className="main-shell" id="overview">
        <header className="topbar">
          <div className="breadcrumb">Workspace <span>/</span> <b>Overview</b></div>
          <div className="topbar-right">
            <div className={`live-badge ${connection}`} role="status" aria-live="polite">
              <span className="status-dot" />{connection === 'connected' ? isVideoReplay ? 'Replay' : 'Live' : 'Disconnected'}
            </div>
            <button className="theme-toggle" onClick={() => setTheme((current) => current === 'dark' ? 'light' : 'dark')} aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`} title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}>
              <span aria-hidden="true">{theme === 'dark' ? '☀' : '☾'}</span><span className="theme-toggle-label">{theme === 'dark' ? 'Light' : 'Dark'}</span>
            </button>
            <span className="topbar-divider" />
            <div className="operator"><span className="operator-avatar">PO</span><span><b>Parking operator</b><small>Control room</small></span></div>
          </div>
        </header>

        <main className="dashboard">
          <section className="page-heading">
            <div>
              <p className="eyebrow">PARKING OPERATIONS</p>
              <h1>Good day, operator <span aria-hidden="true">✦</span></h1>
              <p className="page-subtitle">Camera detections and configured parking-space status.</p>
            </div>
            <div className="heading-actions">
              <span className="updated-label">{lastUpdated ? `Updated ${formatUpdated(lastUpdated)}` : 'Waiting for data'}</span>
              <button className="button-refresh" onClick={() => loadDashboard()} disabled={loading}>
                <span aria-hidden="true">↻</span> {loading ? 'Refreshing' : 'Refresh'}
              </button>
            </div>
          </section>

          <ServiceHealth backend={backendHealth} ai={aiHealth} socket={connection} camera={feedLoading ? 'loading' : feedAvailable ? 'online' : 'offline'} />
          {aiHealth.status === 'outdated' && (
            <div className="notice source-notice restart-notice" role="alert">
              <b>AI service needs a restart</b>
              <p>The service on port 8001 is responding, but it is an older version that does not report the configured parking map.</p>
              <p>1. In the terminal running the AI service, press <kbd>Ctrl</kbd>+<kbd>C</kbd>.</p>
              <p>2. Open a new PowerShell terminal and run:</p>
              <pre><code>{'Set-Location "C:\\Users\\SUNIL KUMAR\\Desktop\\smart-cctv-parking\\ai-service"\n& .\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001'}</code></pre>
              <p>Leave that terminal open, then refresh this dashboard.</p>
            </div>
          )}
          {aiHealth.status === 'online' && (!occupancyVerified || isVideoReplay) && (
            <div className="notice source-notice" role="status">
              {isVideoReplay && replayOccupancyAvailable
                ? `VIDEO REPLAY: showing detection-based estimates for ${configuredSlotIds.length} mapped bays only. This is prerecorded sample footage, not live parking availability.`
                : isVideoReplay
                ? `VIDEO REPLAY: ${aiHealth.cameraId || 'This source'} is prerecorded, not live CCTV. Waiting for a recent occupancy update; mapped bays are shown as unverified. ${configuredSlotIds.length} spaces are mapped from this clip, not your actual facility.`
                : aiHealth.slotConfigError
                  ? `Parking map could not be loaded: ${aiHealth.slotConfigError}`
                  : configuredSlotIds.length && !configuredSlotsPresent
                    ? `Parking occupancy is hidden: ${configuredSlotIds.length} camera spaces are configured, but only ${configuredSlots.length} are registered in the backend.`
                    : !cameraMapSynced && configuredSlotsPresent
                      ? 'Waiting for the live camera to confirm its mapped-space occupancy; saved statuses stay hidden until then.'
                      : backendHealth.status !== 'online'
                        ? 'Backend unavailable; live parking status cannot be verified.'
                        : 'Live occupancy is hidden until a webcam or network camera and its matching parking-space map are connected.'}
            </div>
          )}
          {panelStates.stats.error && (
            <div className="notice error-notice stats-notice" role="alert">
              <span>Summary metrics unavailable: {panelStates.stats.error}</span>
              <button className="text-button" onClick={() => loadDashboard(['stats'])}>Retry</button>
            </div>
          )}

          <section className="stats-grid" aria-label="Facility summary">
            <article className="stat-card stat-green">
              <div className="stat-top"><span>AVAILABLE SPACES</span><span className="stat-icon">⌖</span></div>
              <div className="stat-value">{occupancyVerified ? free : '—'}<small> / {configuredSlotIds.length || '—'}</small></div>
              <div className="stat-foot"><span className={`mini-dot ${occupancyVerified ? 'green-dot' : 'amber-dot'}`} />{occupancyVerified ? replayOccupancyAvailable ? 'Sample replay estimate · not live' : 'Available mapped camera spaces' : `${configuredSlotIds.length} spaces mapped; status unverified`}</div>
            </article>
            <article className="stat-card stat-blue">
              <div className="stat-top"><span>OCCUPIED MAPPED SPACES</span><span className="stat-icon">↗</span></div>
              <div className="stat-value">{occupancyVerified ? occupied : '—'}</div>
              <div className="stat-foot"><span className="mini-dot blue-dot" />{occupancyVerified ? replayOccupancyAvailable ? 'Detected occupied bays · replay' : 'Current camera occupancy' : 'Requires a camera and mapped spaces'}</div>
            </article>
            <article className={`stat-card ${isVideoReplay ? 'stat-blue' : !liveOccupancyVerified || summaryOpen ? 'stat-amber' : 'stat-green'}`}>
              <div className="stat-top"><span>{isVideoReplay ? 'VEHICLES IN CURRENT FRAME' : 'SAVED OPEN ALERTS'}</span><span className="stat-icon">{isVideoReplay ? '▣' : '⚑'}</span></div>
              <div className="stat-value">{isVideoReplay ? detectionSummary?.total ?? '—' : liveOccupancyVerified ? (statsUnavailable || alertsUnavailable ? '—' : stats?.openAlerts ?? open) : '—'}</div>
              <div className="stat-foot"><span className={`mini-dot ${isVideoReplay ? 'blue-dot' : !liveOccupancyVerified || alertsUnavailable || summaryOpen ? 'amber-dot' : 'green-dot'}`} />{isVideoReplay ? detectionSummary ? `${detectionSummary.bikes} bikes · ${detectionSummary.cars} cars tracked` : 'Waiting for current-frame detections' : !liveOccupancyVerified ? 'Current camera alerts not verified' : alertsUnavailable ? 'Alert history unavailable' : summaryOpen ? 'Saved alerts need review' : 'No saved open alerts'}</div>
            </article>
            <article className="stat-card stat-violet">
              <div className="stat-top"><span>{isVideoReplay ? 'VEHICLE CLASS COVERAGE' : 'TODAY’S ENTRIES'}</span><span className="stat-icon">{isVideoReplay ? '◉' : '↗'}</span></div>
              <div className="stat-value">{isVideoReplay ? detectionSummary ? `${detectionSummary.bikes} / ${detectionSummary.cars}` : '—' : liveOccupancyVerified && !statsUnavailable ? stats?.todayEntries ?? '—' : '—'}</div>
              <div className="stat-foot"><span className="mini-dot violet-dot" />{isVideoReplay ? 'Bikes / cars · SUVs are labeled as cars' : liveOccupancyVerified ? 'Backend entries saved today' : 'Current camera entries not verified'}</div>
            </article>
          </section>

          <div className="content-grid">
            <section className="panel camera-panel">
              <div className="panel-heading">
                <div><p className="eyebrow">CAMERA MONITORING</p><h2>Live camera feed</h2></div>
                <span className="camera-tag"><span className="status-dot" /> {cameraSourceLabel} · {aiHealth.cameraId || 'cam-1'}</span>
              </div>
              <div className="camera-view">
                {feedAvailable && <img className={feedLoading ? 'feed-image is-loading' : 'feed-image'} src="/ai/stream" alt={isVideoReplay ? 'Prerecorded parking video with vehicle detections' : 'Parking camera feed with vehicle detections'} onLoad={() => setFeedLoading(false)} onError={() => { setFeedAvailable(false); setFeedLoading(false); }} />}
                {feedLoading ? (
                  <div className="feed-placeholder feed-loading-placeholder" role="status"><span className="loading-spinner" aria-hidden="true" /><b>Connecting to camera…</b><span>Starting the live video stream.</span></div>
                ) : !feedAvailable ? (
                  <div className="feed-placeholder">
                    <span className="camera-placeholder-icon" aria-hidden="true">▣</span>
                    <b>Camera feed is offline</b>
                    <span>Start the AI service to view the live stream.</span>
                    <button className="feed-retry" onClick={() => { setCameraOccupancy(null); setFeedAvailable(true); setFeedLoading(true); }}>Retry connection</button>
                  </div>
                ) : null}
                {feedAvailable && !feedLoading && <span className="feed-live"><span className={`status-dot ${isVideoReplay ? 'replay-dot' : ''}`} /> {isVideoReplay ? 'VIDEO REPLAY' : 'LIVE'}</span>}
              </div>
              <div className="camera-caption"><span><span className={`status-dot ${connection === 'connected' && !isVideoReplay ? 'online' : ''}`} />{isVideoReplay ? 'Recorded video playback' : connection === 'connected' ? 'Connected to facility' : 'Waiting for facility connection'}</span><span>AI-powered monitoring</span></div>
            </section>

            <section className="panel slots-panel" id="parking">
              <div className="panel-heading">
                <div><p className="eyebrow">CAMERA MAP</p><h2>Mapped parking spaces</h2></div>
                <div className="slot-panel-actions">
                  <span className="panel-meta">{replayOccupancyAvailable ? 'Sample replay · not live' : `${configuredSlotIds.length} camera-mapped spaces`}</span>
                  {liveOccupancyVerified && <a className="subtle-link" href="#recommend">Find a spot <span aria-hidden="true">→</span></a>}
                </div>
              </div>
              <div className="slot-summary">
                <span><i className="legend-dot free-legend" />Free <b>{occupancyVerified ? free : '—'}</b></span>
                <span><i className="legend-dot occupied-legend" />Occupied <b>{occupancyVerified ? occupied : '—'}</b></span>
                <span><i className="legend-dot reserved-legend" />Reserved <b>{occupancyVerified ? cameraDisplaySlots.filter((slot) => slot.status === 'reserved').length : '—'}</b></span>
              </div>
              <PanelState loading={panelStates.slots.loading} error={panelStates.slots.error} onRetry={() => loadDashboard(['slots'])}>
                <SlotGrid slots={cameraDisplaySlots} verified={occupancyVerified} />
              </PanelState>
            </section>

            <section className="panel traffic-panel">
              <div className="panel-heading">
                <div><p className="eyebrow">ARRIVAL TRENDS</p><h2>Today’s vehicle activity</h2></div>
                <span className="panel-meta">{isVideoReplay ? 'Saved history · may include prior demo runs' : 'Hourly saved entries · local time'}</span>
              </div>
              <PanelState loading={panelStates.analytics.loading} error={panelStates.analytics.error} onRetry={() => loadDashboard(['analytics'])}>
                <HourlyTraffic data={hourly} />
              </PanelState>
            </section>

            <section className="panel plate-panel">
              <div className="panel-heading">
                <div><p className="eyebrow">NUMBER-PLATE OCR</p><h2>Recently recognized</h2></div>
                <span className={`ocr-mode ${aiHealth.status === 'online' && aiHealth.ocrEnabled ? 'is-enabled' : ''}`}>{aiHealth.status === 'online' ? aiHealth.ocrEnabled ? 'OCR enabled' : 'OCR disabled' : 'AI unavailable'}</span>
              </div>
              <PanelState loading={panelStates.sessions.loading} error={panelStates.sessions.error} onRetry={() => loadDashboard(['sessions'])}>
                <PlateReads sessions={sessions} />
              </PanelState>
            </section>

            <section className="panel recommendation-panel" id="recommend">
              <SlotRecommend slotIds={configuredSlotIds} enabled={liveOccupancyVerified} />
            </section>

            <section className="panel alerts-panel" id="alerts">
              <div className="panel-heading">
                <div><p className="eyebrow">SAFETY &amp; SECURITY</p><h2>Recent saved alerts {liveOccupancyVerified && open > 0 && <span className="heading-count">{open}</span>}</h2></div>
                <span className="panel-meta">{isVideoReplay ? 'Saved history · origin may be unknown' : 'Latest first'}</span>
              </div>
              {actionError && <p className="error inline-error" role="alert">{actionError}</p>}
              <PanelState loading={panelStates.alerts.loading} error={panelStates.alerts.error} onRetry={() => loadDashboard(['alerts'])}>
                <AlertList alerts={alerts} onAck={onAck} />
              </PanelState>
            </section>

            <section className="panel watchlist-panel" id="watchlist">
              <div className="panel-heading">
                <div><p className="eyebrow">VEHICLE SECURITY</p><h2>Watchlist</h2></div>
                <span className="panel-meta">Flagged vehicles</span>
              </div>
              <WatchlistPanel />
            </section>

            <section className="panel activity-panel" id="activity">
              <div className="panel-heading">
                <div><p className="eyebrow">FACILITY ACTIVITY</p><h2>Vehicle check-ins &amp; check-outs</h2></div>
                <span className="panel-meta">Latest 200 records</span>
              </div>
              <PanelState loading={panelStates.sessions.loading} error={panelStates.sessions.error} onRetry={() => loadDashboard(['sessions'])}>
                <SessionTable sessions={sessions} />
              </PanelState>
            </section>
          </div>
          <footer className="page-footer"><span>Parkwise operations dashboard</span><span>Real-time parking intelligence</span></footer>
        </main>
      </div>
    </div>
  );
}
