/** Danh mục bãi đỗ xe chuẩn hóa dùng chung toàn hệ thống AI Console (AUDIT-006 S8 / A-33). */

export interface ParkingLotOption {
  id: string;
  name: string;
  nameKey: 'lotLandmark81' | 'lotVincomCenter' | 'lotSuburbanHub' | 'lotCentral' | 'lotWestGate';
}

export const PARKING_LOTS: readonly ParkingLotOption[] = [
  { id: 'lot_landmark_81', name: 'Landmark 81 Central Parking', nameKey: 'lotLandmark81' },
  { id: 'lot_vincom_center', name: 'Vincom Center Dong Khoi', nameKey: 'lotVincomCenter' },
  { id: 'lot_suburban_hub', name: 'Suburban Transit Hub', nameKey: 'lotSuburbanHub' },
  { id: 'lot_central_01', name: 'Central Lot 01', nameKey: 'lotCentral' },
  { id: 'lot_west_gate', name: 'West Gate Lot', nameKey: 'lotWestGate' },
] as const;

export const DEFAULT_PARKING_LOT_ID = PARKING_LOTS[0].id;

export function resolveLotLabel(
  lot: ParkingLotOption,
  t: { tools?: Record<string, unknown>; copilot?: Record<string, unknown> }
): string {
  const val = t.tools?.[lot.nameKey] ?? t.copilot?.[lot.nameKey];
  return typeof val === 'string' ? val : lot.name;
}
