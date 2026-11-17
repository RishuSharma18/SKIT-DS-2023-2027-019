// Unit tests for session table filter logic
const filterSessions = (sessions, { plate = '', status = '', category = '' }) => {
  return sessions.filter(s => {
    const matchPlate = !plate || (s.plateNumber && s.plateNumber.toLowerCase().includes(plate.toLowerCase()));
    const matchStatus = !status || s.status.toLowerCase() === status.toLowerCase();
    const matchCat = !category || s.vehicleCategory.toLowerCase() === category.toLowerCase();
    return matchPlate && matchStatus && matchCat;
  });
};

describe('Session Filter Logic Tests', () => {
  const mockData = [
    { plateNumber: 'RJ14AB1234', status: 'ACTIVE', vehicleCategory: 'COMPACT_CAR' },
    { plateNumber: 'DL01XY9999', status: 'COMPLETED', vehicleCategory: 'SUV_SEDAN' },
    { plateNumber: 'RJ14CD5678', status: 'COMPLETED', vehicleCategory: 'COMPACT_CAR' }
  ];

  test('filters by plate number partial match', () => {
    const filtered = filterSessions(mockData, { plate: 'RJ14' });
    expect(filtered.length).toBe(2);
  });

  test('filters by status and category', () => {
    const filtered = filterSessions(mockData, { status: 'COMPLETED', category: 'COMPACT_CAR' });
    expect(filtered.length).toBe(1);
    expect(filtered[0].plateNumber).toBe('RJ14CD5678');
  });
});
