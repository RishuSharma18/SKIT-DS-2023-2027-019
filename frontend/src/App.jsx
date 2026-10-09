import { useEffect, useState } from 'react';
import { io } from 'socket.io-client';
import { getSlots, getSessions, getAlerts, ackAlert } from './api.js';
import SlotGrid from './components/SlotGrid.jsx';
import AlertList from './components/AlertList.jsx';
import SessionTable from './components/SessionTable.jsx';
import WatchlistPanel from './components/WatchlistPanel.jsx';
import SlotRecommend from './components/SlotRecommend.jsx';

export default function App() {
  const [slots, setSlots] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [actionError, setActionError] = useState('');

  useEffect(() => {
    getSlots().then(setSlots).catch(console.error);
    getAlerts().then(setAlerts).catch(console.error);
    getSessions().then(setSessions).catch(console.error);

    const socket = io();   // proxied to the backend by Vite
    socket.on('slots:update', setSlots);
    socket.on('alert:new', (a) => setAlerts((prev) => [a, ...prev]));
    socket.on('session:new', (s) => setSessions((prev) => [s, ...prev]));
    socket.on('session:update', (s) =>
      setSessions((prev) => prev.map((p) => (p._id === s._id ? s : p))));
    return () => socket.disconnect();
  }, []);

  const free = slots.filter((s) => s.status === 'free').length;
  const active = sessions.filter((s) => s.status === 'active').length;
  const open = alerts.filter((a) => !a.acknowledged).length;

  const onAck = async (id) => {
    setActionError('');
    try {
      const updated = await ackAlert(id);
      setAlerts((prev) => prev.map((a) => (a._id === id ? updated : a)));
    } catch (err) {
      setActionError(err.message);
    }
  };

  return (
    <div className="page">
      <header>
        <h1>Smart CCTV Parking &amp; Vehicle Safety</h1>
        <div className="stats">
          <span>Free slots: <b>{free}/{slots.length}</b></span>
          <span>Vehicles inside: <b>{active}</b></span>
          <span>Open alerts: <b className={open ? 'bad' : ''}>{open}</b></span>
        </div>
      </header>

      <main>
        <section className="card">
          <h2>Live feed</h2>
          {/* AI service MJPEG preview; start it with `uvicorn app.main:app --port 8000` */}
          <img className="feed" src="http://localhost:8000/stream" alt="Live CCTV feed"
               onError={(e) => { e.currentTarget.style.display = 'none'; }} />
          <p className="muted">Feed appears when the AI service is running.</p>
        </section>

        <section className="card"><h2>Parking slots</h2><SlotGrid slots={slots} /></section>
        <section className="card"><SlotRecommend /></section>
        <section className="card">
          <h2>Alerts</h2>
          {actionError && <p className="error" role="alert">{actionError}</p>}
          <AlertList alerts={alerts} onAck={onAck} />
        </section>
        <section className="card"><WatchlistPanel /></section>
        <section className="card wide"><h2>Check-in / check-out log</h2><SessionTable sessions={sessions} /></section>
      </main>
    </div>
  );
}
