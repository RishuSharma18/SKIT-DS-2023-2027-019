// Unit tests for hourly traffic chart series formatting
const formatHourlyChartSeries = (hourlyData) => {
  return hourlyData.map(d => ({
    label: `${String(d.hour).padStart(2, '0')}:00`,
    value: d.entries || 0,
    isPeak: (d.entries || 0) > 20
  }));
};

describe('Chart Series Formatting Tests', () => {
  test('formats 24-hour labels correctly', () => {
    const raw = [{ hour: 9, entries: 15 }, { hour: 14, entries: 25 }];
    const formatted = formatHourlyChartSeries(raw);
    expect(formatted[0].label).toBe('09:00');
    expect(formatted[0].isPeak).toBe(false);
    expect(formatted[1].isPeak).toBe(true);
  });
});
