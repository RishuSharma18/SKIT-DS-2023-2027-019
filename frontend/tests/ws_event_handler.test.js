// Unit tests for WebSocket event dispatcher
const reduceWsEvent = (state, event) => {
  switch (event.type) {
    case 'slots:update':
      return { ...state, slots: event.data };
    case 'alert:new':
      return { ...state, alerts: [event.data, ...state.alerts] };
    case 'alert:ack':
      return {
        ...state,
        alerts: state.alerts.map(a => a.alertId === event.data.alertId ? { ...a, isAcknowledged: true } : a)
      };
    default:
      return state;
  }
};

describe('WebSocket State Reducer Tests', () => {
  test('handles new alert prepending', () => {
    const initialState = { alerts: [{ alertId: '1' }] };
    const nextState = reduceWsEvent(initialState, { type: 'alert:new', data: { alertId: '2' } });
    expect(nextState.alerts.length).toBe(2);
    expect(nextState.alerts[0].alertId).toBe('2');
  });

  test('handles alert acknowledgment', () => {
    const initialState = { alerts: [{ alertId: '1', isAcknowledged: false }] };
    const nextState = reduceWsEvent(initialState, { type: 'alert:ack', data: { alertId: '1' } });
    expect(nextState.alerts[0].isAcknowledged).toBe(true);
  });
});
