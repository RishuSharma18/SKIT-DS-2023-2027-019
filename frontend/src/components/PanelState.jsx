export default function PanelState({ loading, error, onRetry, children }) {
  if (loading) {
    return (
      <div className="panel-state" role="status">
        <span className="loading-spinner" aria-hidden="true" />
        <span>Loading data…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="panel-state panel-error" role="alert">
        <span>{error}</span>
        <button className="text-button" onClick={onRetry}>Try again</button>
      </div>
    );
  }

  return children;
}
