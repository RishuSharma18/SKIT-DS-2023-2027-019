import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react';
import {
  Activity,
  AlertTriangle,
  ArrowUpRight,
  Bell,
  Bike,
  CalendarDays,
  CarFront,
  Check,
  ChevronDown,
  CircleCheck,
  ExternalLink,
  Filter,
  LayoutDashboard,
  LoaderCircle,
  MapPin,
  Maximize2,
  Moon,
  ParkingCircle,
  Pencil,
  Plus,
  Radio,
  RefreshCw,
  Search,
  ShieldAlert,
  ShieldCheck,
  Siren,
  Sun,
  Trash2,
  Truck,
  Users,
  Wifi,
  WifiOff,
  X,
  Zap,
} from 'lucide-react';
import {
  acknowledgeAlert,
  allocateSlot,
  connectLiveEvents,
  createWatchlistEntry,
  getAlerts,
  getCameraIds,
  getCameraStreamUrl,
  getSessions,
  getSlots,
  getWatchlist,
  normalizeAlert,
  removeWatchlistEntry,
  resolveCameraStreamFallback,
  updateWatchlistEntry,
  type WatchlistInput,
} from './services/api';
import type {
  AlertType,
  ConnectionState,
  LiveEvent,
  ParkingSession,
  ParkingSlot,
  SecurityAlert,
  ToastMessage,
  VehicleCategory,
  WatchlistEntry,
} from './types';

type DashboardTab = 'overview' | 'alerts' | 'history' | 'watchlist';
type DataKey = 'slots' | 'sessions' | 'alerts' | 'watchlist';
type DataState = Record<DataKey, { loading: boolean; error: string; loaded: boolean }>;

const CATEGORY_NAMES: Record<VehicleCategory, string> = {
  TWO_WHEELER: 'Two wheeler',
  COMPACT_CAR: 'Compact car',
  SUV_SEDAN: 'SUV / Sedan',
  HEAVY_VEHICLE: 'Heavy vehicle',
};
const ALERT_NAMES: Record<AlertType, string> = {
  STOLEN_VEHICLE: 'Stolen vehicle',
  ACCIDENT: 'Accident detected',
  WRONG_PARKING: 'Wrong parking',
  OVERSTAY: 'Overstay',
};
const CATEGORIES = Object.keys(CATEGORY_NAMES) as VehicleCategory[];
const INITIAL_DATA_STATE: DataState = {
  slots: { loading: true, error: '', loaded: false },
  sessions: { loading: true, error: '', loaded: false },
  alerts: { loading: true, error: '', loaded: false },
  watchlist: { loading: true, error: '', loaded: false },
};

function formatClock(value: string | Date): string {
  const date = value instanceof Date ? value : new Date(value);
  return Number.isNaN(date.getTime())
    ? '—'
    : date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function formatDateTime(value: string | Date): string {
  const date = value instanceof Date ? value : new Date(value);
  return Number.isNaN(date.getTime())
    ? '—'
    : date.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function durationLabel(seconds: number | null): string {
  if (seconds === null || !Number.isFinite(seconds)) return '—';
  const minutes = Math.max(0, Math.floor(seconds / 60));
  const hours = Math.floor(minutes / 60);
  return hours ? `${hours}h ${minutes % 60}m` : `${minutes}m`;
}

function categoryIcon(category: VehicleCategory, size = 17) {
  const Icon = category === 'TWO_WHEELER'
    ? Bike
    : category === 'HEAVY_VEHICLE'
      ? Truck
      : CarFront;
  return <Icon size={size} strokeWidth={1.8} aria-hidden="true" />;
}

function isUrgent(alert: SecurityAlert): boolean {
  return alert.type === 'STOLEN_VEHICLE' || alert.type === 'ACCIDENT';
}

function cameraLabel(cameraId: string): string {
  return cameraId.replace(/[_-]/g, ' ').toUpperCase();
}

function initialTheme(): 'light' | 'dark' {
  const saved = localStorage.getItem('parkwise-theme');
  if (saved === 'dark' || saved === 'light') return saved;
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function ToastStack({ toasts, onDismiss }: { toasts: ToastMessage[]; onDismiss: (id: string) => void }) {
  return (
    <div className="ops-toasts" aria-live="polite" aria-label="Notifications">
      {toasts.map((toast) => (
        <div className={`ops-toast tone-${toast.tone}`} key={toast.id} role="status">
          <span className="ops-toast-icon">{toast.tone === 'error' ? <AlertTriangle size={17} /> : <CircleCheck size={17} />}</span>
          <span className="ops-toast-copy"><b>{toast.title}</b><small>{toast.message}</small></span>
          <button type="button" onClick={() => onDismiss(toast.id)} aria-label="Dismiss notification"><X size={15} /></button>
        </div>
      ))}
    </div>
  );
}

function SkeletonCard() {
  return <div className="ops-skeleton" aria-label="Loading data"><span /><span /><span /></div>;
}

function CameraFeed({
  cameraId,
  selected,
  onExpand,
  onSelect,
}: {
  cameraId: string;
  selected: boolean;
  onExpand: (cameraId: string) => void;
  onSelect: (cameraId: string) => void;
}) {
  const [source, setSource] = useState(() => getCameraStreamUrl(cameraId));
  const [offline, setOffline] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const fallback = resolveCameraStreamFallback(cameraId);

  useEffect(() => {
    setSource(getCameraStreamUrl(cameraId));
    setOffline(false);
    setLoaded(false);
  }, [cameraId]);

  const onFeedError = () => {
    if (source !== fallback) setSource(fallback);
    else setOffline(true);
  };

  return (
    <article className={`ops-camera-card ${selected ? 'selected' : ''}`} onClick={() => onSelect(cameraId)}>
      <div className="ops-camera-image">
        {!offline ? (
          <img src={source} alt={`${cameraLabel(cameraId)} live CCTV feed`} onLoad={() => setLoaded(true)} onError={onFeedError} />
        ) : (
          <div className="ops-camera-offline"><WifiOff size={20} /><span>Camera feed unavailable</span><small>Check the AI stream service</small></div>
        )}
        {!offline && !loaded && <span className="ops-camera-loading"><LoaderCircle size={15} className="animate-spin" />Connecting to feed</span>}
        {!offline && loaded && <span className="ops-camera-live"><i />LIVE</span>}
        <button className="ops-camera-expand" type="button" onClick={() => onExpand(cameraId)} aria-label={`Expand ${cameraLabel(cameraId)} feed`}><Maximize2 size={15} /></button>
      </div>
      <div className="ops-camera-info"><span><Radio size={14} />{cameraLabel(cameraId)}</span><small>{offline ? 'Offline' : loaded ? 'AI monitoring active' : 'Connecting…'}</small></div>
    </article>
  );
}

function App() {
  const cameraIds = useMemo(() => getCameraIds(), []);
  const [slots, setSlots] = useState<ParkingSlot[]>([]);
  const [sessions, setSessions] = useState<ParkingSession[]>([]);
  const [alerts, setAlerts] = useState<SecurityAlert[]>([]);
  const [watchlist, setWatchlist] = useState<WatchlistEntry[]>([]);
  const [dataState, setDataState] = useState<DataState>(INITIAL_DATA_STATE);
  const [tab, setTab] = useState<DashboardTab>('overview');
  const [connection, setConnection] = useState<ConnectionState>('connecting');
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);
  const [now, setNow] = useState(Date.now());
  const [theme, setTheme] = useState<'light' | 'dark'>(initialTheme);
  const [search, setSearch] = useState('');
  const [sessionFilter, setSessionFilter] = useState<'ALL' | 'ACTIVE' | 'CLOSED'>('ALL');
  const [alertFilter, setAlertFilter] = useState<'ALL' | AlertType>('ALL');
  const [category, setCategory] = useState<VehicleCategory>('COMPACT_CAR');
  const [allocation, setAllocation] = useState<ParkingSlot | null>(null);
  const [allocating, setAllocating] = useState(false);
  const [selectedCamera, setSelectedCamera] = useState(cameraIds[0] || 'CAM_01');
  const [expandedCamera, setExpandedCamera] = useState<string | null>(null);
  const [urgentAlert, setUrgentAlert] = useState<SecurityAlert | null>(null);
  const [acknowledgingId, setAcknowledgingId] = useState('');
  const [editingEntry, setEditingEntry] = useState<WatchlistEntry | null>(null);
  const [watchlistFormOpen, setWatchlistFormOpen] = useState(false);
  const [watchlistBusyId, setWatchlistBusyId] = useState('');
  const [form, setForm] = useState<WatchlistInput>({ plateNumber: '', reason: '', active: true });
  const [formBusy, setFormBusy] = useState(false);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const pushToast = useCallback((title: string, message: string, tone: ToastMessage['tone'] = 'success') => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    setToasts((current) => [...current.slice(-3), { id, title, message, tone }]);
    window.setTimeout(() => setToasts((current) => current.filter((toast) => toast.id !== id)), 5_500);
  }, []);

  const loadDashboard = useCallback(async (quiet = false) => {
    setDataState((current) => Object.fromEntries(
      Object.entries(current).map(([key, value]) => [key, { ...value, loading: !quiet, error: '' }]),
    ) as DataState);

    const resources = [
      { key: 'slots' as const, load: async () => { setSlots(await getSlots()); }, label: 'parking spaces' },
      { key: 'sessions' as const, load: async () => { setSessions(await getSessions()); }, label: 'vehicle history' },
      { key: 'alerts' as const, load: async () => { setAlerts(await getAlerts()); }, label: 'security alerts' },
      { key: 'watchlist' as const, load: async () => { setWatchlist(await getWatchlist()); }, label: 'watchlist' },
    ];
    const results = await Promise.allSettled(resources.map((resource) => resource.load()));
    let failed = false;
    results.forEach((result, index) => {
      const resource = resources[index];
      if (result.status === 'fulfilled') {
        setDataState((current) => ({
          ...current,
          [resource.key]: { loading: false, error: '', loaded: true },
        }));
      } else {
        failed = true;
        const message = result.reason instanceof Error ? result.reason.message : 'Service request failed';
        setDataState((current) => ({
          ...current,
          [resource.key]: { ...current[resource.key], loading: false, error: message },
        }));
      }
    });
    if (results.some((result) => result.status === 'fulfilled')) setUpdatedAt(new Date());
    if (failed && !quiet) pushToast('Some data is unavailable', 'A panel could not refresh. Use its retry action.', 'warning');
  }, [pushToast]);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem('parkwise-theme', theme);
  }, [theme]);

  useEffect(() => {
    void loadDashboard();
    const poll = window.setInterval(() => void loadDashboard(true), 30_000);
    const timer = window.setInterval(() => setNow(Date.now()), 60_000);
    return () => {
      window.clearInterval(poll);
      window.clearInterval(timer);
    };
  }, [loadDashboard]);

  const handleLiveEvent = useCallback((event: LiveEvent) => {
    const name = event.name.toLowerCase();
    const raw = typeof event.payload === 'object' && event.payload !== null
      ? event.payload as Record<string, unknown>
      : {};
    const alertCandidate = raw.alert_type || raw.alertType
      || ['alert:new', 'alert', 'stolen_vehicle', 'accident', 'crash', 'wrong_parking', 'overstay'].includes(name);
    if (alertCandidate) {
      const alert = normalizeAlert(raw.alert ?? raw);
      setAlerts((current) => [alert, ...current.filter((item) => item.id !== alert.id)]);
      pushToast(ALERT_NAMES[alert.type], alert.message, isUrgent(alert) ? 'error' : 'warning');
      if (isUrgent(alert)) {
        setUrgentAlert(alert);
        playAlertTone();
      }
    }

    if (name.includes('slot') || name === 'entry' || name === 'exit' || name === 'event') {
      void Promise.allSettled([getSlots(), getSessions()]).then(([slotResult, sessionResult]) => {
        if (slotResult.status === 'fulfilled') setSlots(slotResult.value);
        if (sessionResult.status === 'fulfilled') setSessions(sessionResult.value);
      });
    } else if (name.includes('session') || name === 'entry' || name === 'exit') {
      void getSessions().then(setSessions).catch(() => undefined);
    }
    setUpdatedAt(new Date());
  }, [pushToast]);

  useEffect(() => connectLiveEvents(handleLiveEvent, setConnection), [handleLiveEvent]);

  const availableSlots = slots.filter((slot) => slot.status === 'AVAILABLE');
  const occupiedSlots = slots.filter((slot) => slot.status === 'OCCUPIED');
  const activeSessions = sessions.filter((session) => session.status === 'ACTIVE');
  const todaysAlerts = alerts.filter((alert) => new Date(alert.timestamp).toDateString() === new Date().toDateString());
  const openAlerts = alerts.filter((alert) => !alert.acknowledged);
  const availableByCategory = CATEGORIES.map((item) => ({
    category: item,
    count: availableSlots.filter((slot) => slot.category === item).length,
  }));
  const filteredAlerts = alerts.filter((alert) => alertFilter === 'ALL' || alert.type === alertFilter);
  const filteredSessions = sessions.filter((session) => {
    const matchesStatus = sessionFilter === 'ALL' || session.status === sessionFilter;
    const haystack = `${session.plateNumber || ''} ${session.slotId || ''} ${CATEGORY_NAMES[session.category]}`.toLowerCase();
    return matchesStatus && haystack.includes(search.trim().toLowerCase());
  });

  const acknowledge = async (alert: SecurityAlert) => {
    setAcknowledgingId(alert.id);
    try {
      const saved = await acknowledgeAlert(alert.id);
      setAlerts((current) => current.map((item) => item.id === saved.id ? saved : item));
      setUrgentAlert((current) => current?.id === saved.id ? null : current);
      pushToast('Alert acknowledged', `${ALERT_NAMES[saved.type]} marked for operator follow-up.`);
    } catch (error) {
      pushToast('Could not acknowledge alert', getErrorMessage(error), 'error');
    } finally {
      setAcknowledgingId('');
    }
  };

  const recommendSlot = async () => {
    setAllocating(true);
    setAllocation(null);
    try {
      const result = await allocateSlot(category);
      setAllocation(result.slot);
      pushToast(
        result.slot ? 'Slot recommendation ready' : 'No compatible space available',
        result.slot ? `${result.slot.id} is currently available. Assignment is not reserved.` : 'Try a different vehicle category.',
        result.slot ? 'success' : 'warning',
      );
    } catch (error) {
      pushToast('Allocation request failed', getErrorMessage(error), 'error');
    } finally {
      setAllocating(false);
    }
  };

  const openAddForm = () => {
    setEditingEntry(null);
    setForm({ plateNumber: '', reason: '', active: true });
    setWatchlistFormOpen(true);
  };

  const openEditForm = (entry: WatchlistEntry) => {
    setEditingEntry(entry);
    setForm({ plateNumber: entry.plateNumber, reason: entry.reason, active: entry.active });
    setWatchlistFormOpen(true);
  };

  const saveWatchlistEntry = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormBusy(true);
    try {
      const saved = editingEntry
        ? await updateWatchlistEntry(editingEntry.id, form)
        : await createWatchlistEntry(form);
      setWatchlist((current) => [
        saved,
        ...current.filter((entry) => entry.id !== saved.id),
      ]);
      setWatchlistFormOpen(false);
      pushToast(editingEntry ? 'Watchlist entry updated' : 'Vehicle added to watchlist', saved.plateNumber);
    } catch (error) {
      pushToast('Watchlist update failed', getErrorMessage(error), 'error');
    } finally {
      setFormBusy(false);
    }
  };

  const toggleWatchlistEntry = async (entry: WatchlistEntry) => {
    setWatchlistBusyId(entry.id);
    try {
      const updated = await updateWatchlistEntry(entry.id, {
        plateNumber: entry.plateNumber,
        reason: entry.reason,
        active: !entry.active,
      });
      setWatchlist((current) => current.map((item) => item.id === entry.id ? updated : item));
      pushToast(updated.active ? 'Watchlist monitoring enabled' : 'Watchlist monitoring paused', updated.plateNumber);
    } catch (error) {
      pushToast('Could not update watchlist status', getErrorMessage(error), 'error');
    } finally {
      setWatchlistBusyId('');
    }
  };

  const deleteWatchlistEntry = async (entry: WatchlistEntry) => {
    if (!window.confirm(`Remove ${entry.plateNumber} from the watchlist?`)) return;
    setWatchlistBusyId(entry.id);
    try {
      await removeWatchlistEntry(entry.id);
      setWatchlist((current) => current.filter((item) => item.id !== entry.id));
      pushToast('Watchlist entry removed', entry.plateNumber);
    } catch (error) {
      pushToast('Could not remove watchlist entry', getErrorMessage(error), 'error');
    } finally {
      setWatchlistBusyId('');
    }
  };

  const retryResource = (key: DataKey) => {
    const loaders: Record<DataKey, () => Promise<void>> = {
      slots: async () => { setSlots(await getSlots()); },
      sessions: async () => { setSessions(await getSessions()); },
      alerts: async () => { setAlerts(await getAlerts()); },
      watchlist: async () => { setWatchlist(await getWatchlist()); },
    };
    setDataState((current) => ({ ...current, [key]: { ...current[key], loading: true, error: '' } }));
    void loaders[key]()
      .then(() => {
        setDataState((current) => ({ ...current, [key]: { loading: false, error: '', loaded: true } }));
      })
      .catch((error: unknown) => setDataState((current) => ({
        ...current,
        [key]: {
          ...current[key],
          loading: false,
          error: getErrorMessage(error),
        },
      })));
  };

  return (
    <div className="ops-shell min-h-screen bg-slate-50 text-slate-900">
      <aside className="ops-sidebar">
        <a className="ops-brand" href="#overview" onClick={() => setTab('overview')}>
          <span className="ops-brand-mark"><ParkingCircle size={21} /></span>
          <span>parkwise<span className="ops-brand-dot">.</span><small>SMART PARKING</small></span>
        </a>
        <div className="ops-sidebar-label">WORKSPACE</div>
        <nav className="ops-nav" aria-label="Main navigation">
          <NavButton active={tab === 'overview'} label="Overview" icon={<LayoutDashboard size={17} />} onClick={() => setTab('overview')} />
          <NavButton active={tab === 'alerts'} label="Alert center" icon={<Bell size={17} />} badge={openAlerts.length || undefined} onClick={() => setTab('alerts')} />
          <NavButton active={tab === 'history'} label="Vehicle history" icon={<Activity size={17} />} onClick={() => setTab('history')} />
          <NavButton active={tab === 'watchlist'} label="Watchlist" icon={<ShieldCheck size={17} />} onClick={() => setTab('watchlist')} />
        </nav>
        <div className="ops-sidebar-bottom">
          <div className="ops-connection-card">
            <span className={`ops-connection-icon ${connection}`}><ConnectionIcon state={connection} /></span>
            <span><b>Live connection</b><small>{connectionText(connection)}</small></span>
          </div>
          <span className="ops-sidebar-foot">PARKING OPERATIONS <span>v2.0</span></span>
        </div>
      </aside>

      <main className="ops-main">
        <header className="ops-topbar">
          <div className="ops-crumb">Workspace <span>/</span> <b>{TAB_LABELS[tab]}</b></div>
          <div className="ops-topbar-actions">
            <div className={`ops-live-pill ${connection}`}><i />{connectionText(connection)}</div>
            <span className="ops-topbar-divider" />
            <span className="ops-date"><CalendarDays size={15} />{new Date().toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' })}</span>
            <button className="ops-icon-button" type="button" onClick={() => setTheme((current) => current === 'dark' ? 'light' : 'dark')} aria-label="Toggle color theme">
              {theme === 'dark' ? <Sun size={17} /> : <Moon size={17} />}
            </button>
            <span className="ops-avatar">PO</span>
          </div>
        </header>

        <div className="ops-page">
          <section className="ops-page-heading">
            <div>
              <p className="ops-eyebrow">{tab === 'overview' ? 'PARKING OPERATIONS' : 'SECURITY & FACILITY'}</p>
              <h1>{PAGE_TITLE[tab]}</h1>
              <p className="ops-page-subtitle">{PAGE_SUBTITLE[tab]}</p>
            </div>
            <div className="ops-heading-actions">
              <span className="ops-update-time">{updatedAt ? `Synced ${formatClock(updatedAt)}` : 'Waiting for services'}</span>
              <button className="ops-button ops-button-quiet" type="button" onClick={() => void loadDashboard()} disabled={Object.values(dataState).some((state) => state.loading)}>
                <RefreshCw size={15} className={Object.values(dataState).some((state) => state.loading) ? 'animate-spin' : ''} />Refresh
              </button>
            </div>
          </section>

          {tab === 'overview' && (
            <>
              <section className="ops-kpis" aria-label="Facility key performance indicators">
                <KpiCard label="Total capacity" value={dataState.slots.loaded ? slots.length : '—'} icon={<ParkingCircle size={17} />} tone="green" footer={`${occupiedSlots.length} currently occupied`} />
                <article className="ops-kpi ops-kpi-category">
                  <div className="ops-kpi-heading"><span>AVAILABLE BY CATEGORY</span><span className="ops-kpi-icon tone-blue"><Filter size={16} /></span></div>
                  <div className="ops-category-kpis">
                    {availableByCategory.map((item) => (
                      <span key={item.category} title={CATEGORY_NAMES[item.category]}>{categoryIcon(item.category, 14)}<b>{dataState.slots.loaded ? item.count : '—'}</b></span>
                    ))}
                  </div>
                  <div className="ops-kpi-footer"><i className="dot dot-blue" />Free spaces by vehicle size</div>
                </article>
                <KpiCard label="Active vehicles" value={dataState.sessions.loaded ? activeSessions.length : '—'} icon={<Users size={17} />} tone="violet" footer={`${occupiedSlots.length} spaces occupied`} />
                <KpiCard label="Today's alerts" value={dataState.alerts.loaded ? todaysAlerts.length : '—'} icon={<ShieldAlert size={17} />} tone={todaysAlerts.length ? 'amber' : 'green'} footer={`${openAlerts.length} need attention`} />
              </section>

              <div className="ops-dashboard-grid">
                <section className="ops-panel ops-cameras-panel">
                  <PanelHeading eyebrow="LIVE MONITORING" title="Camera feeds" trailing={<label className="ops-camera-switcher"><span>Focus camera</span><select value={selectedCamera} onChange={(event) => setSelectedCamera(event.target.value)}>{cameraIds.map((id) => <option key={id} value={id}>{cameraLabel(id)}</option>)}</select><ChevronDown size={13} /></label>} />
                  <div className="ops-camera-grid">
                    {(cameraIds.length > 1 ? [selectedCamera, ...cameraIds.filter((id) => id !== selectedCamera)] : [selectedCamera]).map((cameraId) => <CameraFeed key={cameraId} cameraId={cameraId} selected={selectedCamera === cameraId} onExpand={setExpandedCamera} onSelect={setSelectedCamera} />)}
                  </div>
                </section>

                <section className="ops-panel ops-map-panel" id="parking-map">
                  <PanelHeading eyebrow="FACILITY MAP" title="Space utilization" trailing={<span className="ops-live-caption"><i />Live</span>} />
                  <div className="ops-slot-legend">
                    <StatusLegend status="AVAILABLE" label="Available" />
                    <StatusLegend status="OCCUPIED" label="Occupied" />
                    <StatusLegend status="RESERVED" label="Reserved" />
                    <StatusLegend status="VIOLATION" label="Violation" />
                  </div>
                  {dataState.slots.loading && !dataState.slots.loaded ? <SkeletonCard /> : dataState.slots.error && !dataState.slots.loaded
                    ? <PanelError message={dataState.slots.error} onRetry={() => retryResource('slots')} />
                    : slots.length ? <div className="ops-slot-grid">{slots.map((slot) => <SlotTile key={slot.id} slot={slot} />)}</div>
                      : <EmptyState icon={<ParkingCircle size={22} />} title="No parking spaces configured" copy="Seed parking spaces in the backend to display the facility map." />}
                </section>

                <section className="ops-panel ops-allocation-panel">
                  <PanelHeading eyebrow="QUICK ACTION" title="Recommend a parking slot" trailing={<span className="ops-recommend-tag"><Zap size={13} />Allocation</span>} />
                  <p className="ops-panel-copy">Simulate an entry and ask the backend for a compatible available space.</p>
                  <label className="ops-field-label" htmlFor="allocate-category">VEHICLE CATEGORY</label>
                  <div className="ops-category-select">
                    <span>{categoryIcon(category, 18)}</span>
                    <select id="allocate-category" value={category} onChange={(event) => { setCategory(event.target.value as VehicleCategory); setAllocation(null); }}>
                      {CATEGORIES.map((item) => <option value={item} key={item}>{CATEGORY_NAMES[item]}</option>)}
                    </select>
                    <ChevronDown size={15} />
                  </div>
                  <button className="ops-button ops-button-primary ops-allocate-button" type="button" onClick={() => void recommendSlot()} disabled={allocating}>
                    {allocating ? <LoaderCircle size={16} className="animate-spin" /> : <Zap size={16} />}
                    {allocating ? 'Finding a space…' : 'Simulate entry & recommend'}
                  </button>
                  {allocation && <div className="ops-allocation-result"><span className="ops-result-check"><Check size={15} /></span><span><small>RECOMMENDED SLOT · NOT RESERVED</small><b>{allocation.id}</b></span><span className="ops-status-chip available">Available</span></div>}
                  {!allocation && <div className="ops-allocation-foot"><ShieldCheck size={14} />Slot status is rechecked by the backend on allocation.</div>}
                </section>

                <section className="ops-panel ops-alert-panel" id="alert-center">
                  <PanelHeading eyebrow="SECURITY CENTER" title="Live alerts" trailing={<button type="button" className="ops-text-link" onClick={() => setTab('alerts')}>View all <ArrowUpRight size={14} /></button>} />
                  <AlertFilters value={alertFilter} onChange={setAlertFilter} />
                  <AlertFeed alerts={filteredAlerts.slice(0, 5)} loading={dataState.alerts.loading} error={dataState.alerts.error} retry={() => retryResource('alerts')} onAcknowledge={acknowledge} acknowledgingId={acknowledgingId} />
                </section>

                <section className="ops-panel ops-history-panel">
                  <PanelHeading eyebrow="VEHICLE ACTIVITY" title="Recent entries & exits" trailing={<button type="button" className="ops-text-link" onClick={() => setTab('history')}>History <ArrowUpRight size={14} /></button>} />
                  <SessionTable sessions={sessions.slice(0, 5)} now={now} loading={dataState.sessions.loading} error={dataState.sessions.error} retry={() => retryResource('sessions')} />
                </section>
                <section className="ops-panel ops-watchlist-summary">
                  <PanelHeading eyebrow="VEHICLE SECURITY" title="Watchlist" trailing={<button type="button" className="ops-text-link" onClick={() => setTab('watchlist')}>Manage <ArrowUpRight size={14} /></button>} />
                  <div className="ops-watchlist-summary-body">
                    <span className="ops-watchlist-shield"><ShieldAlert size={21} /></span>
                    <span><b>{dataState.watchlist.loaded ? watchlist.filter((entry) => entry.active).length : '—'} active flags</b><small>Plates are checked when vehicle OCR is received.</small></span>
                    <button className="ops-icon-button" type="button" onClick={openAddForm} aria-label="Add a vehicle to watchlist"><Plus size={17} /></button>
                  </div>
                  {watchlist.slice(0, 3).map((entry) => <div className="ops-watchlist-mini" key={entry.id}><span className={entry.active ? 'ops-mini-active' : 'ops-mini-paused'} />{entry.plateNumber}<small>{entry.active ? 'Active' : 'Paused'}</small></div>)}
                </section>
              </div>
            </>
          )}

          {tab === 'alerts' && (
            <section className="ops-panel ops-page-panel">
              <PanelHeading eyebrow="SECURITY CENTER" title={`Alerts & incidents${openAlerts.length ? ` · ${openAlerts.length} open` : ''}`} trailing={<span className="ops-live-caption"><i />Live feed</span>} />
              <AlertFilters value={alertFilter} onChange={setAlertFilter} />
              <AlertFeed alerts={filteredAlerts} loading={dataState.alerts.loading} error={dataState.alerts.error} retry={() => retryResource('alerts')} onAcknowledge={acknowledge} acknowledgingId={acknowledgingId} expanded />
            </section>
          )}

          {tab === 'history' && (
            <section className="ops-panel ops-page-panel">
              <PanelHeading eyebrow="FACILITY ACTIVITY" title="Vehicle entry & exit history" trailing={<span className="ops-record-count">{filteredSessions.length} records</span>} />
              <div className="ops-table-toolbar">
                <label className="ops-search"><Search size={16} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search plate, slot or category" aria-label="Search vehicle history" /></label>
                <label className="ops-filter-select"><Filter size={15} /><select value={sessionFilter} onChange={(event) => setSessionFilter(event.target.value as typeof sessionFilter)}><option value="ALL">All vehicles</option><option value="ACTIVE">Currently inside</option><option value="CLOSED">Completed visits</option></select><ChevronDown size={14} /></label>
              </div>
              <SessionTable sessions={filteredSessions} now={now} loading={dataState.sessions.loading} error={dataState.sessions.error} retry={() => retryResource('sessions')} full />
            </section>
          )}

          {tab === 'watchlist' && (
            <section className="ops-panel ops-page-panel">
              <PanelHeading eyebrow="VEHICLE SECURITY" title="Stolen vehicle watchlist" trailing={<button className="ops-button ops-button-primary" type="button" onClick={openAddForm}><Plus size={16} />Add plate</button>} />
              <p className="ops-panel-copy">Manage flagged license plates monitored by OCR. Changes are saved to the backend watchlist.</p>
              <WatchlistTable entries={watchlist} loading={dataState.watchlist.loading} error={dataState.watchlist.error} retry={() => retryResource('watchlist')} busyId={watchlistBusyId} onEdit={openEditForm} onToggle={toggleWatchlistEntry} onDelete={deleteWatchlistEntry} />
            </section>
          )}

          <footer className="ops-footer"><span>Parkwise operations dashboard</span><span>Backend allocation · AI-assisted monitoring</span></footer>
        </div>
      </main>

      {expandedCamera && <CameraModal cameraId={expandedCamera} onClose={() => setExpandedCamera(null)} />}
      {watchlistFormOpen && <WatchlistModal form={form} editing={Boolean(editingEntry)} busy={formBusy} onChange={setForm} onClose={() => setWatchlistFormOpen(false)} onSubmit={saveWatchlistEntry} />}
      {urgentAlert && <UrgentAlertModal alert={urgentAlert} busy={acknowledgingId === urgentAlert.id} onAcknowledge={() => void acknowledge(urgentAlert)} onClose={() => setUrgentAlert(null)} />}
      <ToastStack toasts={toasts} onDismiss={(id) => setToasts((current) => current.filter((toast) => toast.id !== id))} />
    </div>
  );
}

const TAB_LABELS: Record<DashboardTab, string> = {
  overview: 'Overview',
  alerts: 'Alert center',
  history: 'Vehicle history',
  watchlist: 'Watchlist',
};
const PAGE_TITLE: Record<DashboardTab, string> = {
  overview: 'Good day, operator',
  alerts: 'Alert center',
  history: 'Vehicle history',
  watchlist: 'Watchlist management',
};
const PAGE_SUBTITLE: Record<DashboardTab, string> = {
  overview: 'Monitor parking activity, camera feeds, and safety alerts in real time.',
  alerts: 'Review incidents, verify camera snapshots, and acknowledge operator actions.',
  history: 'Search vehicle arrivals, departures, and active parking sessions.',
  watchlist: 'Add, edit, pause, or remove plates monitored by security operations.',
};

function NavButton({
  active,
  label,
  icon,
  badge,
  onClick,
}: {
  active: boolean;
  label: string;
  icon: React.ReactNode;
  badge?: number;
  onClick: () => void;
}) {
  return <button className={`ops-nav-link ${active ? 'active' : ''}`} type="button" onClick={onClick}>{icon}<span>{label}</span>{badge ? <b>{badge}</b> : null}</button>;
}

function ConnectionIcon({ state }: { state: ConnectionState }) {
  return state === 'connected' ? <Wifi size={16} /> : state === 'connecting' ? <LoaderCircle size={16} className="animate-spin" /> : <WifiOff size={16} />;
}

function connectionText(state: ConnectionState): string {
  return state === 'connected' ? 'Live' : state === 'connecting' ? 'Connecting' : 'Disconnected';
}

function KpiCard({
  label,
  value,
  icon,
  tone,
  footer,
}: {
  label: string;
  value: number | string;
  icon: React.ReactNode;
  tone: string;
  footer: string;
}) {
  return (
    <article className="ops-kpi">
      <div className="ops-kpi-heading"><span>{label}</span><span className={`ops-kpi-icon tone-${tone}`}>{icon}</span></div>
      <b className="ops-kpi-value">{value}</b>
      <div className="ops-kpi-footer"><i className={`dot dot-${tone}`} />{footer}</div>
    </article>
  );
}

function PanelHeading({
  eyebrow,
  title,
  trailing,
}: {
  eyebrow: string;
  title: string;
  trailing?: React.ReactNode;
}) {
  return <div className="ops-panel-heading"><div><p className="ops-eyebrow">{eyebrow}</p><h2>{title}</h2></div>{trailing}</div>;
}

function StatusLegend({ status, label }: { status: ParkingSlot['status']; label: string }) {
  return <span><i className={`ops-legend-dot ${status.toLowerCase()}`} />{label}</span>;
}

function SlotTile({ slot }: { slot: ParkingSlot }) {
  return (
    <article className={`ops-slot ${slot.status.toLowerCase()}`} title={`${slot.id} · ${slot.status} · ${CATEGORY_NAMES[slot.category]}`}>
      <div className="ops-slot-top"><span>{categoryIcon(slot.category, 15)}</span><span className="ops-slot-state-dot" /></div>
      <b>{slot.id}</b>
      <small>{CATEGORY_NAMES[slot.category]}</small>
    </article>
  );
}

function PanelError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return <div className="ops-panel-error" role="alert"><AlertTriangle size={18} /><span>{message}</span><button type="button" onClick={onRetry}>Retry</button></div>;
}

function EmptyState({ icon, title, copy }: { icon: React.ReactNode; title: string; copy: string }) {
  return <div className="ops-empty"><span>{icon}</span><b>{title}</b><small>{copy}</small></div>;
}

function AlertFilters({
  value,
  onChange,
}: {
  value: 'ALL' | AlertType;
  onChange: (value: 'ALL' | AlertType) => void;
}) {
  return (
    <div className="ops-alert-filters" aria-label="Filter alerts by type">
      {(['ALL', 'STOLEN_VEHICLE', 'ACCIDENT', 'WRONG_PARKING', 'OVERSTAY'] as const).map((filter) => (
        <button className={value === filter ? 'selected' : ''} key={filter} type="button" onClick={() => onChange(filter)}>
          {filter === 'ALL' ? 'All alerts' : ALERT_NAMES[filter]}
        </button>
      ))}
    </div>
  );
}

function AlertFeed({
  alerts,
  loading,
  error,
  retry,
  onAcknowledge,
  acknowledgingId,
  expanded = false,
}: {
  alerts: SecurityAlert[];
  loading: boolean;
  error: string;
  retry: () => void;
  onAcknowledge: (alert: SecurityAlert) => void;
  acknowledgingId: string;
  expanded?: boolean;
}) {
  if (loading && !alerts.length) return <SkeletonCard />;
  if (error && !alerts.length) return <PanelError message={error} onRetry={retry} />;
  if (!alerts.length) return <EmptyState icon={<ShieldCheck size={23} />} title="No alerts to show" copy="New safety events will appear here as they arrive." />;
  return (
    <div className={`ops-alert-list ${expanded ? 'expanded' : ''}`}>
      {alerts.map((alert) => (
        <article className={`ops-alert-card ${alert.type.toLowerCase()} ${alert.acknowledged ? 'acknowledged' : ''}`} key={alert.id}>
          <span className={`ops-alert-icon ${isUrgent(alert) ? 'urgent' : ''}`}>{isUrgent(alert) ? <Siren size={18} /> : <AlertTriangle size={18} />}</span>
          <div className="ops-alert-content">
            <div className="ops-alert-title-row"><b>{ALERT_NAMES[alert.type]}</b><span className={`ops-severity ${alert.severity.toLowerCase()}`}>{alert.severity}</span></div>
            <p>{alert.message}</p>
            <div className="ops-alert-meta">
              {alert.plateNumber && <code>{alert.plateNumber}</code>}
              <span><Radio size={12} />{cameraLabel(alert.cameraId)}</span>
              {alert.slotId && <span><MapPin size={12} />{alert.slotId}</span>}
              <time dateTime={alert.timestamp}>{formatDateTime(alert.timestamp)}</time>
            </div>
            {alert.snapshotUrl && <a className="ops-snapshot-link" href={alert.snapshotUrl} target="_blank" rel="noreferrer"><ExternalLink size={13} />Open vehicle snapshot</a>}
          </div>
          {!alert.acknowledged && <button className="ops-button ops-button-quiet ops-ack-button" type="button" onClick={() => onAcknowledge(alert)} disabled={acknowledgingId === alert.id}>{acknowledgingId === alert.id ? <LoaderCircle size={14} className="animate-spin" /> : <Check size={14} />}Acknowledge</button>}
          {alert.acknowledged && <span className="ops-acknowledged"><Check size={13} />Acknowledged</span>}
        </article>
      ))}
    </div>
  );
}

function SessionTable({
  sessions,
  now,
  loading,
  error,
  retry,
  full = false,
}: {
  sessions: ParkingSession[];
  now: number;
  loading: boolean;
  error: string;
  retry: () => void;
  full?: boolean;
}) {
  if (loading && !sessions.length) return <SkeletonCard />;
  if (error && !sessions.length) return <PanelError message={error} onRetry={retry} />;
  if (!sessions.length) return <EmptyState icon={<Users size={22} />} title="No vehicle activity yet" copy="Entries and exits will appear once the system detects vehicles." />;
  return (
    <div className={`ops-table-wrap ${full ? 'full' : ''}`}>
      <table className="ops-table">
        <thead><tr><th>PLATE NUMBER</th><th>CATEGORY</th><th>ASSIGNED SLOT</th><th>CHECK-IN</th><th>CHECK-OUT</th><th>DURATION</th><th>STATUS</th></tr></thead>
        <tbody>
          {sessions.map((session) => (
            <tr key={session.id}>
              <td><span className="ops-plate">{session.plateNumber || 'Plate pending'}</span></td>
              <td><span className="ops-category-cell">{categoryIcon(session.category, 15)}{CATEGORY_NAMES[session.category]}</span></td>
              <td>{session.slotId || '—'}</td>
              <td>{formatDateTime(session.checkInTime)}</td>
              <td>{session.checkOutTime ? formatDateTime(session.checkOutTime) : '—'}</td>
              <td>{durationLabel(
                session.status === 'ACTIVE'
                  ? Math.max(0, Math.round((now - Date.parse(session.checkInTime)) / 1000))
                  : session.durationSeconds,
              )}</td>
              <td><span className={`ops-session-status ${session.status.toLowerCase()}`}>{session.overstay && <span className="ops-overstay">Overstay</span>}{session.status === 'ACTIVE' ? 'Live' : 'Completed'}</span></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function WatchlistTable({
  entries,
  loading,
  error,
  retry,
  busyId,
  onEdit,
  onToggle,
  onDelete,
}: {
  entries: WatchlistEntry[];
  loading: boolean;
  error: string;
  retry: () => void;
  busyId: string;
  onEdit: (entry: WatchlistEntry) => void;
  onToggle: (entry: WatchlistEntry) => void;
  onDelete: (entry: WatchlistEntry) => void;
}) {
  if (loading && !entries.length) return <SkeletonCard />;
  if (error && !entries.length) return <PanelError message={error} onRetry={retry} />;
  if (!entries.length) return <EmptyState icon={<ShieldCheck size={24} />} title="Watchlist is clear" copy="Add a plate to flag it for operator attention when OCR identifies a match." />;
  return (
    <div className="ops-watchlist-table">
      <div className="ops-watchlist-head"><span>LICENSE PLATE</span><span>REASON</span><span>STATUS</span><span>ADDED</span><span>ACTIONS</span></div>
      {entries.map((entry) => (
        <div className="ops-watchlist-row" key={entry.id}>
          <span className="ops-watchlist-plate"><ShieldAlert size={16} /><code>{entry.plateNumber}</code></span>
          <span>{entry.reason || 'Flagged for review'}</span>
          <span><button type="button" className={`ops-toggle ${entry.active ? 'on' : ''}`} aria-pressed={entry.active} onClick={() => onToggle(entry)} disabled={busyId === entry.id}><i />{entry.active ? 'Active' : 'Paused'}</button></span>
          <span>{formatDateTime(entry.createdAt)}</span>
          <span className="ops-watchlist-actions">
            <button className="ops-icon-button" type="button" onClick={() => onEdit(entry)} aria-label={`Edit ${entry.plateNumber}`}><Pencil size={15} /></button>
            <button className="ops-icon-button danger" type="button" onClick={() => onDelete(entry)} aria-label={`Remove ${entry.plateNumber}`} disabled={busyId === entry.id}><Trash2 size={15} /></button>
          </span>
        </div>
      ))}
    </div>
  );
}

function CameraModal({ cameraId, onClose }: { cameraId: string; onClose: () => void }) {
  const [source, setSource] = useState(getCameraStreamUrl(cameraId));
  const fallback = resolveCameraStreamFallback(cameraId);
  const [offline, setOffline] = useState(false);
  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [onClose]);
  return (
    <div className="ops-modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section className="ops-camera-modal" role="dialog" aria-modal="true" aria-label={`${cameraLabel(cameraId)} full-screen camera`}>
        <header><span><Radio size={16} />{cameraLabel(cameraId)} · LIVE CAMERA</span><button type="button" className="ops-icon-button" onClick={onClose} aria-label="Close camera"><X size={19} /></button></header>
        {offline ? <div className="ops-camera-modal-offline"><WifiOff size={28} />Camera feed unavailable</div> : <img src={source} alt={`${cameraLabel(cameraId)} full-screen live feed`} onError={() => source !== fallback ? setSource(fallback) : setOffline(true)} />}
      </section>
    </div>
  );
}

function WatchlistModal({
  form,
  editing,
  busy,
  onChange,
  onClose,
  onSubmit,
}: {
  form: WatchlistInput;
  editing: boolean;
  busy: boolean;
  onChange: (form: WatchlistInput) => void;
  onClose: () => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [onClose]);
  return (
    <div className="ops-modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <form className="ops-form-modal" role="dialog" aria-modal="true" aria-labelledby="watchlist-modal-title" onSubmit={onSubmit}>
        <header><span className="ops-modal-icon"><ShieldAlert size={19} /></span><button type="button" className="ops-icon-button" onClick={onClose} aria-label="Close form"><X size={18} /></button></header>
        <h2 id="watchlist-modal-title">{editing ? 'Edit watchlist plate' : 'Add plate to watchlist'}</h2>
        <p>Flagged license plates are checked when the OCR service identifies a vehicle.</p>
        <label className="ops-form-field"><span>LICENSE PLATE</span><input value={form.plateNumber} onChange={(event) => onChange({ ...form, plateNumber: event.target.value.toUpperCase() })} placeholder="RJ14AB1234" maxLength={16} autoFocus required /></label>
        <label className="ops-form-field"><span>REASON</span><input value={form.reason} onChange={(event) => onChange({ ...form, reason: event.target.value })} placeholder="Reported stolen, operator note…" maxLength={120} /></label>
        <label className="ops-check-field"><input type="checkbox" checked={form.active} onChange={(event) => onChange({ ...form, active: event.target.checked })} /><span>Active monitoring</span></label>
        <div className="ops-modal-actions"><button className="ops-button ops-button-quiet" type="button" onClick={onClose}>Cancel</button><button className="ops-button ops-button-primary" type="submit" disabled={busy || !form.plateNumber.trim()}>{busy ? <LoaderCircle size={15} className="animate-spin" /> : editing ? <Check size={15} /> : <Plus size={15} />}{editing ? 'Save changes' : 'Add to watchlist'}</button></div>
      </form>
    </div>
  );
}

function UrgentAlertModal({
  alert,
  busy,
  onAcknowledge,
  onClose,
}: {
  alert: SecurityAlert;
  busy: boolean;
  onAcknowledge: () => void;
  onClose: () => void;
}) {
  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [onClose]);
  return (
    <div className="ops-modal-backdrop ops-urgent-backdrop" role="presentation">
      <section className="ops-urgent-modal" role="alertdialog" aria-modal="true" aria-labelledby="urgent-alert-title">
        <header><span><Siren size={17} />URGENT SECURITY ALERT</span><button className="ops-icon-button" type="button" onClick={onClose} aria-label="Dismiss alert"><X size={18} /></button></header>
        {alert.snapshotUrl ? <img className="ops-urgent-snapshot" src={alert.snapshotUrl} alt="Cropped vehicle snapshot for this alert" /> : <div className="ops-urgent-no-snapshot"><AlertTriangle size={25} /><span>Snapshot unavailable</span></div>}
        <div className="ops-urgent-content">
          <p className="ops-eyebrow">{ALERT_NAMES[alert.type]}</p>
          <h2 id="urgent-alert-title">{alert.message}</h2>
          <div className="ops-urgent-details">
            {alert.plateNumber && <span><small>PLATE</small><b>{alert.plateNumber}</b></span>}
            <span><small>CAMERA</small><b>{cameraLabel(alert.cameraId)}</b></span>
            <span><small>TIME</small><b>{formatDateTime(alert.timestamp)}</b></span>
          </div>
          <button className="ops-button ops-button-danger" type="button" onClick={onAcknowledge} disabled={busy}>{busy ? <LoaderCircle size={16} className="animate-spin" /> : <ShieldCheck size={16} />}{busy ? 'Saving response…' : 'Acknowledge / Dispatch'}</button>
        </div>
      </section>
    </div>
  );
}

function playAlertTone() {
  try {
    const AudioContextConstructor = window.AudioContext
      || (window as typeof window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!AudioContextConstructor) return;
    const context = new AudioContextConstructor();
    const oscillator = context.createOscillator();
    const gain = context.createGain();
    oscillator.type = 'sine';
    oscillator.frequency.value = 880;
    gain.gain.setValueAtTime(0.0001, context.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.12, context.currentTime + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, context.currentTime + 0.38);
    oscillator.connect(gain);
    gain.connect(context.destination);
    oscillator.start();
    oscillator.stop(context.currentTime + 0.4);
    oscillator.onended = () => void context.close();
  } catch {
    // Audio is best-effort; the visual alert remains available.
  }
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Unexpected service error.';
}

export default App;
