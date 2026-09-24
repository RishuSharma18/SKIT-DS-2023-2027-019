// Unit tests for timestamp and duration formatters
const formatDuration = (minutes) => {
  if (minutes < 1) return '< 1 min';
  const hrs = Math.floor(minutes / 60);
  const mins = Math.round(minutes % 60);
  if (hrs === 0) return `${mins}m`;
  return `${hrs}h ${mins}m`;
};

describe('Duration Formatter Tests', () => {
  test('formats minutes correctly', () => {
    expect(formatDuration(45)).toBe('45m');
    expect(formatDuration(125)).toBe('2h 5m');
    expect(formatDuration(0.4)).toBe('< 1 min');
    expect(formatDuration(1440)).toBe('24h 0m');
  });
});
