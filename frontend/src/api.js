async function request(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.error || `Request failed (${response.status})`);
  }
  return response.status === 204 ? null : response.json();
}

export const getSlots = () => request('/api/slots');
export const getSessions = (status) =>
  request(`/api/sessions${status ? `?status=${status}` : ''}`);
export const getAlerts = () => request('/api/alerts');
export const ackAlert = (id) => request(`/api/alerts/${id}/ack`, { method: 'PATCH' });
export const getWatchlist = () => request('/api/watchlist');
export const addWatchlistEntry = (entry) =>
  request('/api/watchlist', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(entry),
  });
export const deleteWatchlistEntry = (id) =>
  request(`/api/watchlist/${id}`, { method: 'DELETE' });
export const recommendSlot = (type) =>
  request(`/api/slots/recommend?type=${encodeURIComponent(type)}`);
