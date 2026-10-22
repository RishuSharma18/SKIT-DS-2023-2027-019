// Unit tests for overstay warning badge calculation
const getOverstayIndicator = (durationMinutes, maxAllowedMinutes = 240) => {
  if (durationMinutes >= maxAllowedMinutes) {
    return { state: 'EXCEEDED', color: 'bg-red-500 text-white animate-pulse' };
  }
  if (durationMinutes >= maxAllowedMinutes * 0.8) {
    return { state: 'WARNING', color: 'bg-yellow-500/20 text-yellow-400' };
  }
  return { state: 'NORMAL', color: 'bg-emerald-500/20 text-emerald-400' };
};

describe('Overstay Indicator Tests', () => {
  test('returns normal for low duration', () => {
    expect(getOverstayIndicator(120).state).toBe('NORMAL');
  });

  test('returns warning near threshold', () => {
    expect(getOverstayIndicator(200).state).toBe('WARNING');
  });

  test('returns exceeded past threshold', () => {
    expect(getOverstayIndicator(245).state).toBe('EXCEEDED');
  });
});
