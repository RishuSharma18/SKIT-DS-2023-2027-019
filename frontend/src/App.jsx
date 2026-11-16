import { useCallback, useEffect, useState } from 'react';
import { io } from 'socket.io-client';
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
  const [lastUpdated, setLastUpdated] = useState(null);
  const [feedAvailable, setFeedAvailable] = useState(true);
  const [feedLoading, setFeedLoading] = useState(true);
  const [backendHealth, setBackendHealth] = useState({ status: 'loading' });
  const [aiHealth, setAiHealth] = useState({ status: 'loading', ocrEnabled: false, durationModelAvailable: false });
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
    setAiHealth(aiResult.status === 'fulfilled'
      ? {
        status: 'online',
        ocrEnabled: aiResult.value.ocrEnabled,
        durationModelAvailable: aiResult.value.durationModelAvailable,
        durationModelMetrics: aiResult.value.durationModelMetrics,
      }
      : { status: 'offline', ocrEnabled: false, durationModelAvailable: false, error: aiResult.reason.message });
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

    const socket = io();
    socket.on('connect', () => setConnection('connected'));
    socket.on('disconnect', () => setConnection('disconnected'));
    socket.on('connect_error', () => setConnection('disconnected'));
    socket.on('slots:update', (nextSlots) => {
      setSlots(nextSlots);
      setPanelStates((current) => ({ ...current, slots: { loading: false, error: '' } }));
      setLastUpdated(new Date());
      loadDashboard(['stats']);
    });
    socket.on('alert:new', (alert) => {
      setAlerts((current) => [alert, ...current.filter((item) => item._id !== alert._id)]);
      setPanelStates((current) => ({ ...current, alerts: { loading: false, error: '' } }));
      setLastUpdated(new Date());
      loadDashboard(['stats']);
    });
    socket.on('session:new', (session) => {
      setSessions((current) => [session, ...current.filter((item) => item._id !== session._id)]);
      setPanelStates((current) => ({ ...current, sessions: { loading: false, error: '' } }));
      setLastUpdated(new Date());
      loadDashboard(['stats', 'analytics']);
    });
    socket.on('session:update', (session) => {
      setSessions((current) => current.map((item) => (item._id === session._id ? session : item)));
      setPanelStates((current) => ({ ...current, sessions: { loading: false, error: '' } }));
      setLastUpdated(new Date());
      loadDashboard(['stats']);
    });

    return () => {
      window.clearInterval(healthInterval);
      socket.disconnect();
    };
  }, [loadDashboard, refreshHealth]);

  const free = slots.filter((slot) => slot.status === 'free').length;
  const occupied = slots.filter((slot) => slot.status === 'occupied').length;
  const active = sessions.filter((session) => session.status === 'active').length;
  const open = alerts.filter((alert) => !alert.acknowledged).length;
  const slotsUnavailable = panelStates.slots.loading || Boolean(panelStates.slots.error);
  const alertsUnavailable = panelStates.alerts.loading || Boolean(panelStates.alerts.error);
  const statsUnavailable = panelStates.stats.loading || Boolean(panelStates.stats.error);
  const summaryOpen = statsUnavailable ? open : stats?.openAlerts ?? open;

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
          <a className="side-link" href="#alerts"><span aria-hidden="true">◉</span> Alerts{open > 0 && <span className="nav-count">{open}</span>}</a>
          <a className="side-link" href="#watchlist"><span aria-hidden="true">☆</span> Watchlist</a>
          <a className="side-link" href="#activity"><span aria-hidden="true">↗</span> Activity</a>
        </nav>
        <div className="sidebar-bottom">
          <div className="system-card">
            <span className={`status-dot ${connection === 'connected' ? 'online' : ''}`} />
            <div><b>System status</b><span>{connection === 'connected' ? 'All systems operational' : connection === 'connecting' ? 'Connecting to server…' : 'Live updates unavailable'}</span></div>
          </div>
          <div className="sidebar-foot">PARKING OPERATIONS <span>v1.0</span></div>
        </div>
      </aside>

      <div className="main-shell" id="overview">
        <header className="topbar">
          <div className="breadcrumb">Workspace <span>/</span> <b>Overview</b></div>
          <div className="topbar-right">
            <div className={`live-badge ${connection}`} role="status" aria-live="polite">
              <span className="status-dot" />{connection === 'connected' ? 'Live' : 'Disconnected'}
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
              <p className="page-subtitle">A live view of your parking facility and vehicle safety.</p>
            </div>
            <div className="heading-actions">
              <span className="updated-label">{lastUpdated ? `Updated ${formatUpdated(lastUpdated)}` : 'Waiting for data'}</span>
              <button className="button-refresh" onClick={() => loadDashboard()} disabled={loading}>
                <span aria-hidden="true">↻</span> {loading ? 'Refreshing' : 'Refresh'}
              </button>
            </div>
          </section>

          <ServiceHealth backend={backendHealth} ai={aiHealth} socket={connection} camera={feedLoading ? 'loading' : feedAvailable ? 'online' : 'offline'} />
          {panelStates.stats.error && (
            <div className="notice error-notice stats-notice" role="alert">
              <span>Summary metrics unavailable: {panelStates.stats.error}</span>
              <button className="text-button" onClick={() => loadDashboard(['stats'])}>Retry</button>
            </div>
          )}

          <section className="stats-grid" aria-label="Facility summary">
            <article className="stat-card stat-green">
              <div className="stat-top"><span>AVAILABLE SPACES</span><span className="stat-icon">⌖</span></div>
              <div className="stat-value">{statsUnavailable ? (slotsUnavailable ? '—' : free) : stats?.freeSlots}<small> / {statsUnavailable ? (slotsUnavailable ? '—' : slots.length) : stats?.totalSlots}</small></div>
              <div className="stat-foot"><span className={`mini-dot ${slotsUnavailable ? 'amber-dot' : 'green-dot'}`} />{slotsUnavailable ? 'Slot availability unavailable' : 'Ready for incoming vehicles'}</div>
            </article>
            <article className="stat-card stat-blue">
              <div className="stat-top"><span>VEHICLES INSIDE</span><span className="stat-icon">↗</span></div>
              <div className="stat-value">{statsUnavailable ? (panelStates.sessions.loading || panelStates.sessions.error ? '—' : active) : stats?.activeVehicles}</div>
              <div className="stat-foot"><span className="mini-dot blue-dot" />{slotsUnavailable ? 'Occupancy unavailable' : `${occupied} parking ${occupied === 1 ? 'space' : 'spaces'} occupied`}</div>
            </article>
            <article className={`stat-card ${summaryOpen ? 'stat-amber' : 'stat-green'}`}>
              <div className="stat-top"><span>OPEN ALERTS</span><span className="stat-icon">⚑</span></div>
              <div className="stat-value">{statsUnavailable ? (panelStates.alerts.loading || panelStates.alerts.error ? '—' : open) : stats?.openAlerts}</div>
              <div className="stat-foot"><span className={`mini-dot ${alertsUnavailable || summaryOpen ? 'amber-dot' : 'green-dot'}`} />{alertsUnavailable ? 'Alert status unavailable' : summaryOpen ? 'Needs operator attention' : 'You’re all caught up'}</div>
            </article>
            <article className="stat-card stat-violet">
              <div className="stat-top"><span>TODAY’S ENTRIES</span><span className="stat-icon">↗</span></div>
              <div className="stat-value">{statsUnavailable ? '—' : stats?.todayEntries ?? '—'}</div>
              <div className="stat-foot"><span className="mini-dot violet-dot" />{statsUnavailable ? 'Daily count unavailable' : 'Vehicles checked in today'}</div>
            </article>
          </section>

          <div className="content-grid">
            <section className="panel camera-panel">
              <div className="panel-heading">
                <div><p className="eyebrow">CAMERA MONITORING</p><h2>Live camera feed</h2></div>
                <span className="camera-tag"><span className="status-dot" /> CAM 01</span>
              </div>
              <div className="camera-view">
                {feedAvailable && <img className={feedLoading ? 'feed-image is-loading' : 'feed-image'} src="http://localhost:8000/stream" alt="Live parking CCTV feed" onLoad={() => setFeedLoading(false)} onError={() => { setFeedAvailable(false); setFeedLoading(false); }} />}
                {feedLoading ? (
                  <div className="feed-placeholder feed-loading-placeholder" role="status"><span className="loading-spinner" aria-hidden="true" /><b>Connecting to camera…</b><span>Starting the live video stream.</span></div>
                ) : !feedAvailable ? (
                  <div className="feed-placeholder">
                    <span className="camera-placeholder-icon" aria-hidden="true">▣</span>
                    <b>Camera feed is offline</b>
                    <span>Start the AI service to view the live stream.</span>
                    <button className="feed-retry" onClick={() => { setFeedAvailable(true); setFeedLoading(true); }}>Retry connection</button>
                  </div>
                ) : null}
                {feedAvailable && !feedLoading && <span className="feed-live"><span className="status-dot" /> LIVE</span>}
              </div>
              <div className="camera-caption"><span><span className={`status-dot ${connection === 'connected' ? 'online' : ''}`} />{connection === 'connected' ? 'Connected to facility' : 'Waiting for facility connection'}</span><span>AI-powered monitoring</span></div>
            </section>

            <section className="panel slots-panel" id="parking">
              <div className="panel-heading">
                <div><p className="eyebrow">FACILITY MAP</p><h2>Parking availability</h2></div>
                <a className="subtle-link" href="#recommend">Find a spot <span aria-hidden="true">→</span></a>
              </div>
              <div className="slot-summary">
                <span><i className="legend-dot free-legend" />Free <b>{slotsUnavailable ? '—' : free}</b></span>
                <span><i className="legend-dot occupied-legend" />Occupied <b>{slotsUnavailable ? '—' : occupied}</b></span>
                <span><i className="legend-dot reserved-legend" />Reserved <b>{slotsUnavailable ? '—' : slots.filter((slot) => slot.status === 'reserved').length}</b></span>
              </div>
              <PanelState loading={panelStates.slots.loading} error={panelStates.slots.error} onRetry={() => loadDashboard(['slots'])}>
                <SlotGrid slots={slots} />
              </PanelState>
            </section>

            <section className="panel traffic-panel">
              <div className="panel-heading">
                <div><p className="eyebrow">ARRIVAL TRENDS</p><h2>Today’s vehicle activity</h2></div>
                <span className="panel-meta">Hourly entries · local time</span>
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
              <SlotRecommend />
            </section>

            <section className="panel alerts-panel" id="alerts">
              <div className="panel-heading">
                <div><p className="eyebrow">SAFETY &amp; SECURITY</p><h2>Recent alerts {open > 0 && <span className="heading-count">{open}</span>}</h2></div>
                <span className="panel-meta">Latest first</span>
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
