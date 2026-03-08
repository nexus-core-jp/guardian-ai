export interface User {
  id: string;
  lineId?: string;
  name: string;
  email?: string;
  avatarUrl?: string;
  onboardingCompleted: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface Child {
  id: string;
  parentId: string;
  name: string;
  nickname?: string;
  schoolId?: string;
  schoolName?: string;
  grade?: number;
  gpsDeviceType?: string;
  gpsDeviceId?: string;
  avatarUrl?: string;
  createdAt: string;
  updatedAt: string;
}

export interface School {
  id: string;
  name: string;
  address: string;
  latitude: number;
  longitude: number;
  distanceFromHome?: number;
}

export interface Location {
  latitude: number;
  longitude: number;
  accuracy?: number;
  timestamp: string;
  source: 'gps_device' | 'app' | 'manual';
}

export interface ChildLocation {
  childId: string;
  childName: string;
  location: Location;
  status: 'at_home' | 'at_school' | 'on_route' | 'moving' | 'unknown';
  statusLabel: string;
  batteryLevel?: number;
}

export interface RoutePoint {
  latitude: number;
  longitude: number;
  riskLevel: 'safe' | 'caution' | 'danger';
}

export interface SafeRoute {
  id: string;
  childId: string;
  homeLocation: Location;
  schoolLocation: Location;
  points: RoutePoint[];
  estimatedWalkMinutes: number;
  overallRiskLevel: 'safe' | 'caution' | 'danger';
  createdAt: string;
}

export interface DangerZone {
  id: string;
  latitude: number;
  longitude: number;
  radius: number;
  type: 'suspicious_person' | 'traffic' | 'dark_road' | 'other';
  typeLabel: string;
  description?: string;
  reportedBy: string;
  reportedAt: string;
  expiresAt?: string;
  confirmed: boolean;
  confirmCount: number;
}

export interface Alert {
  id: string;
  userId: string;
  childId?: string;
  type: 'route_deviation' | 'danger_zone' | 'sos' | 'arrival' | 'departure' | 'community_report' | 'system';
  severity: 'info' | 'warning' | 'critical';
  title: string;
  message: string;
  location?: Location;
  read: boolean;
  createdAt: string;
}

export interface DangerReport {
  type: 'suspicious_person' | 'traffic' | 'dark_road' | 'other';
  description?: string;
  latitude: number;
  longitude: number;
}

export interface OnboardingRequest {
  homeLatitude: number;
  homeLongitude: number;
  homeAddress: string;
  schoolId: string;
  gpsDeviceType?: string;
  childName: string;
  childGrade?: number;
}

export interface LoginResponse {
  accessToken: string;
  refreshToken: string;
  user: User;
}

export interface HomeLocation {
  latitude: number;
  longitude: number;
  address: string;
}

export interface NotificationPreferences {
  routeDeviation: boolean;
  dangerZone: boolean;
  arrival: boolean;
  departure: boolean;
  communityReports: boolean;
}
