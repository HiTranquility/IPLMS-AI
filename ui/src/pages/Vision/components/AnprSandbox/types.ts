export type VehicleType = 'car_sedan' | 'car_suv' | 'motorbike' | 'truck' | 'unknown';

export type PlateColor = 'white' | 'yellow' | 'blue' | 'red';

export interface AnprResult {
  plateNumber: string;
  confidence?: number;
  plateColor?: PlateColor;
  vehicleType: string;
  cropPlateImageUrl?: string;
  originalImageUrl?: string;
  eventId?: string;
  timestamp?: string;
  latencyMs?: number;
}

export interface AntiFraudVerification {
  isMatched: boolean;
  similarityScore?: number;
  mismatchReason: string;
  expectedType: string;
  currentType: string;
  verifiedAt: string;
}

export interface SamplePlatePreset {
  id: string;
  name: string;
  plateNumber: string;
  vehicleType: VehicleType;
  plateColor: PlateColor;
  isTwoTier?: boolean;
}

export interface LaneOption {
  id: string;
  name: string;
}
