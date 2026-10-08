const json = (r) => r.json();
export const getSlots = () => fetch('/api/slots').then(json);
export const getSessions = (status) =>
  fetch(`/api/sessions${status ? `?status=${status}` : ''}`).then(json);
export const getAlerts = () => fetch('/api/alerts').then(json);
export const ackAlert = (id) => fetch(`/api/alerts/${id}/ack`, { method: 'PATCH' }).then(json);
