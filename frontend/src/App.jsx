import { useCallback, useEffect, useState } from 'react';
import { io } from 'socket.io-client';
import { ackAlert, getAlerts, getSessions, getSlots } from './api.js';
import AlertList from './components/AlertList.jsx';
import SessionTable from './components/SessionTable.jsx';
import SlotGrid from './components/SlotGrid.jsx';
import SlotRecommend from './components/SlotRecommend.jsx';
import WatchlistPanel from './components/WatchlistPanel.jsx';

const formatUpdated = (date) => date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

export default function App() {
  const [slots, setSlots] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [actionError, setActionError] = useState('');
  const [connection, setConnection] = useState('connecting');
  const [lastUpdated, setLastUpdated] = useState(null);
  const [feedAvailable, setFeedAvailable] = useState(true);

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setLoadError('');
    const results = await Promise.allSettled([getSlots(), getAlerts(), getSessions()]);
    const setters = [setSlots, setAlerts, setSessions];
    const labels = ['parking slots', 'alerts', 'sessions'];
    const failures = [];

    results.forEach((result, index) => {
      if (result.status === 'fulfilled') setters[index](result.value);
      else failures.push(`${labels[index]}: ${result.reason.message}`);
    });

    if (failures.length) setLoadError(`Could not load ${failures.join('; ')}.`);
    setLastUpdated(new Date());
    setLoading(false);
  }, []);

  useEffect(() => {
    loadDashboard();

    const socket = io();
    socket.on('connect', () => setConnection('connected'));
    socket.on('disconnect', () => setConnection('disconnected'));
    socket.on('connect_error', () => setConnection('disconnected'));
    socket.on('slots:update', (nextSlots) => {
      setSlots(nextSlots);
      setLastUpdated(new Date());
    });
    socket.on('alert:new', (alert) => {
      setAlerts((current) => [alert, ...current.filter((item) => item._id !== alert._id)]);
      setLastUpdated(new Date());
    });
    socket.on('session:new', (session) => {
      setSessions((current) => [session, ...current.filter((item) => item._id !== session._id)]);
      setLastUpdated(new Date());
    });
    socket.on('session:update', (session) => {
      setSessions((current) => current.map((item) => (item._id === session._id ? session : item)));
      setLastUpdated(new Date());
    });

    return () => socket.disconnect();
  }, [loadDashboard]);

  const free = slots.filter((slot) => slot.status === 'free').length;
  const occupied = slots.filter((slot) => slot.status === 'occupied').length;
  const active = sessions.filter((session) => session.status === 'active').length;
  const open = alerts.filter((alert) => !alert.acknowledged).length;

  const onAck = async (id) => {
    setActionError('');
    try {
      const updated = await ackAlert(id);
      setAlerts((current) => current.map((alert) => (alert._id === id ? updated : alert)));
    } catch (error) {
      setActionError(error.message);
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
            <div className={`live-badge ${connection}`}><span className="status-dot" />{connection === 'connected' ? 'LIVE UPDATES' : connection === 'connecting' ? 'CONNECTING' : 'OFFLINE'}</div>
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
              <button className="button-refresh" onClick={loadDashboard} disabled={loading}>
                <span aria-hidden="true">↻</span> {loading ? 'Refreshing' : 'Refresh'}
              </button>
            </div>
          </section>

          {loadError && (
            <div className="notice error-notice" role="alert">
              <span>{loadError}</span><button className="text-button" onClick={loadDashboard}>Try again</button>
            </div>
          )}
          {actionError && <div className="notice error-notice" role="alert">{actionError}</div>}

          <section className="stats-grid" aria-label="Facility summary">
            <article className="stat-card stat-green">
              <div className="stat-top"><span>AVAILABLE SPACES</span><span className="stat-icon">⌖</span></div>
              <div className="stat-value">{loading && !slots.length ? '—' : free}<small> / {slots.length}</small></div>
              <div className="stat-foot"><span className="mini-dot green-dot" />Ready for incoming vehicles</div>
            </article>
            <article className="stat-card stat-blue">
              <div className="stat-top"><span>VEHICLES INSIDE</span><span className="stat-icon">↗</span></div>
              <div className="stat-value">{loading && !sessions.length ? '—' : active}</div>
              <div className="stat-foot"><span className="mini-dot blue-dot" />{occupied} parking {occupied === 1 ? 'space' : 'spaces'} occupied</div>
            </article>
            <article className={`stat-card ${open ? 'stat-amber' : 'stat-green'}`}>
              <div className="stat-top"><span>OPEN ALERTS</span><span className="stat-icon">⚑</span></div>
              <div className="stat-value">{loading && !alerts.length ? '—' : open}</div>
              <div className="stat-foot"><span className={`mini-dot ${open ? 'amber-dot' : 'green-dot'}`} />{open ? 'Needs operator attention' : 'You’re all caught up'}</div>
            </article>
            <article className="stat-card stat-violet">
              <div className="stat-top"><span>TOTAL SPACES</span><span className="stat-icon">▤</span></div>
              <div className="stat-value">{loading && !slots.length ? '—' : slots.length}</div>
              <div className="stat-foot"><span className="mini-dot violet-dot" />Across all parking zones</div>
            </article>
          </section>

          <div className="content-grid">
            <section className="panel camera-panel">
              <div className="panel-heading">
                <div><p className="eyebrow">CAMERA MONITORING</p><h2>Live camera feed</h2></div>
                <span className="camera-tag"><span className="status-dot" /> CAM 01</span>
              </div>
              <div className="camera-view">
                {feedAvailable ? (
                  <img src="http://localhost:8000/stream" alt="Live parking CCTV feed" onLoad={() => setFeedAvailable(true)} onError={() => setFeedAvailable(false)} />
                ) : (
                  <div className="feed-placeholder">
                    <span className="camera-placeholder-icon" aria-hidden="true">▣</span>
                    <b>Camera feed is offline</b>
                    <span>Start the AI service to view the live stream.</span>
                    <button className="feed-retry" onClick={() => setFeedAvailable(true)}>Retry connection</button>
                  </div>
                )}
                {feedAvailable && <span className="feed-live"><span className="status-dot" /> LIVE</span>}
              </div>
              <div className="camera-caption"><span><span className={`status-dot ${connection === 'connected' ? 'online' : ''}`} />{connection === 'connected' ? 'Connected to facility' : 'Waiting for facility connection'}</span><span>AI-powered monitoring</span></div>
            </section>

            <section className="panel slots-panel" id="parking">
              <div className="panel-heading">
                <div><p className="eyebrow">FACILITY MAP</p><h2>Parking availability</h2></div>
                <a className="subtle-link" href="#recommend">Find a spot <span aria-hidden="true">→</span></a>
              </div>
              <div className="slot-summary">
                <span><i className="legend-dot free-legend" />Free <b>{free}</b></span>
                <span><i className="legend-dot occupied-legend" />Occupied <b>{occupied}</b></span>
                <span><i className="legend-dot reserved-legend" />Reserved <b>{slots.filter((slot) => slot.status === 'reserved').length}</b></span>
              </div>
              <SlotGrid slots={slots} />
            </section>

            <section className="panel recommendation-panel" id="recommend">
              <SlotRecommend />
            </section>

            <section className="panel alerts-panel" id="alerts">
              <div className="panel-heading">
                <div><p className="eyebrow">SAFETY &amp; SECURITY</p><h2>Recent alerts {open > 0 && <span className="heading-count">{open}</span>}</h2></div>
                <span className="panel-meta">Latest first</span>
              </div>
              <AlertList alerts={alerts} onAck={onAck} />
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
              <SessionTable sessions={sessions} />
            </section>
          </div>
          <footer className="page-footer"><span>Parkwise operations dashboard</span><span>Real-time parking intelligence</span></footer>
        </main>
      </div>
    </div>
  );
}
