// Unit tests for layout dimension calculators
const calculateGridColumns = (width) => {
  if (width < 640) return 2;
  if (width < 1024) return 4;
  if (width < 1440) return 6;
  return 8;
};

describe('Grid Column Calculator Tests', () => {
  test('returns 2 columns for mobile', () => {
    expect(calculateGridColumns(375)).toBe(2);
  });

  test('returns 4 columns for tablet', () => {
    expect(calculateGridColumns(768)).toBe(4);
  });

  test('returns 6 columns for desktop', () => {
    expect(calculateGridColumns(1200)).toBe(6);
  });
});
