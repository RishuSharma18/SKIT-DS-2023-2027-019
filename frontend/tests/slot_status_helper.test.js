// Unit tests for slot status helper and badge classes
const getSlotStatusBadge = (status) => {
  switch (status) {
    case 'AVAILABLE':
      return { label: 'Available', color: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' };
    case 'OCCUPIED':
      return { label: 'Occupied', color: 'bg-red-500/20 text-red-400 border-red-500/30' };
    case 'RESERVED':
      return { label: 'Reserved', color: 'bg-amber-500/20 text-amber-400 border-amber-500/30' };
    case 'VIOLATION':
      return { label: 'Violation', color: 'bg-purple-500/20 text-purple-400 border-purple-500/30' };
    default:
      return { label: 'Unknown', color: 'bg-slate-500/20 text-slate-400 border-slate-500/30' };
  }
};

describe('Slot Status Helper Tests', () => {
  test('returns emerald badge for AVAILABLE', () => {
    const badge = getSlotStatusBadge('AVAILABLE');
    expect(badge.label).toBe('Available');
    expect(badge.color).toContain('emerald');
  });

  test('returns red badge for OCCUPIED', () => {
    const badge = getSlotStatusBadge('OCCUPIED');
    expect(badge.label).toBe('Occupied');
    expect(badge.color).toContain('red');
  });

  test('returns fallback for unknown status', () => {
    const badge = getSlotStatusBadge('OFFLINE');
    expect(badge.label).toBe('Unknown');
  });
});
