// Unit tests for plate input mask formatter
const maskLicensePlate = (input) => {
  if (!input) return '';
  return input.toUpperCase().replace(/[^A-Z0-9]/g, '');
};

describe('License Plate Input Mask Tests', () => {
  test('uppercases and strips spaces/hyphens', () => {
    expect(maskLicensePlate('rj 14 ab-1234')).toBe('RJ14AB1234');
    expect(maskLicensePlate('dl-01-xy-9999')).toBe('DL01XY9999');
  });
});
