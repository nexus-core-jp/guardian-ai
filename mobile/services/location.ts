import { Platform } from 'react-native';
import { WS_URL } from '../constants';
import type { ChildLocation, Location } from '../types';

let ExpoLocation: typeof import('expo-location') | null = null;
if (Platform.OS !== 'web') {
  ExpoLocation = require('expo-location');
}

export async function requestLocationPermission(): Promise<boolean> {
  if (!ExpoLocation) return false;
  const { status: foregroundStatus } = await ExpoLocation.requestForegroundPermissionsAsync();
  if (foregroundStatus !== 'granted') {
    return false;
  }
  return true;
}

export async function requestBackgroundLocationPermission(): Promise<boolean> {
  if (!ExpoLocation) return false;
  const { status } = await ExpoLocation.requestBackgroundPermissionsAsync();
  return status === 'granted';
}

export async function getCurrentLocation(): Promise<Location | null> {
  if (Platform.OS === 'web') {
    // Web: use browser geolocation API
    return new Promise((resolve) => {
      if (!navigator.geolocation) {
        resolve(null);
        return;
      }
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          resolve({
            latitude: pos.coords.latitude,
            longitude: pos.coords.longitude,
            accuracy: pos.coords.accuracy ?? undefined,
            timestamp: new Date(pos.timestamp).toISOString(),
            source: 'app',
          });
        },
        () => resolve(null),
        { enableHighAccuracy: true, timeout: 10000 }
      );
    });
  }

  try {
    const hasPermission = await requestLocationPermission();
    if (!hasPermission) return null;

    const location = await ExpoLocation!.getCurrentPositionAsync({
      accuracy: ExpoLocation!.Accuracy.High,
    });

    return {
      latitude: location.coords.latitude,
      longitude: location.coords.longitude,
      accuracy: location.coords.accuracy ?? undefined,
      timestamp: new Date(location.timestamp).toISOString(),
      source: 'app',
    };
  } catch {
    return null;
  }
}

export async function reverseGeocode(
  latitude: number,
  longitude: number
): Promise<string> {
  if (!ExpoLocation) {
    return `${latitude.toFixed(6)}, ${longitude.toFixed(6)}`;
  }
  try {
    const results = await ExpoLocation.reverseGeocodeAsync({ latitude, longitude });
    if (results.length > 0) {
      const addr = results[0];
      const parts = [
        addr.region,
        addr.city,
        addr.district,
        addr.street,
        addr.streetNumber,
      ].filter(Boolean);
      return parts.join('') || `${latitude.toFixed(6)}, ${longitude.toFixed(6)}`;
    }
    return `${latitude.toFixed(6)}, ${longitude.toFixed(6)}`;
  } catch {
    return `${latitude.toFixed(6)}, ${longitude.toFixed(6)}`;
  }
}

export class ChildLocationSocket {
  private ws: WebSocket | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private onUpdate: ((location: ChildLocation) => void) | null = null;
  private childId: string;
  private token: string;

  constructor(childId: string, token: string) {
    this.childId = childId;
    this.token = token;
  }

  connect(onUpdate: (location: ChildLocation) => void): void {
    this.onUpdate = onUpdate;
    this.doConnect();
  }

  private doConnect(): void {
    try {
      this.ws = new WebSocket(
        `${WS_URL}/ws/child/${this.childId}/location?token=${this.token}`
      );

      this.ws.onopen = () => {
        console.log('WebSocket connected for child:', this.childId);
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as ChildLocation;
          this.onUpdate?.(data);
        } catch {
          console.warn('Failed to parse WebSocket message');
        }
      };

      this.ws.onclose = () => {
        this.scheduleReconnect();
      };

      this.ws.onerror = () => {
        this.ws?.close();
      };
    } catch {
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) return;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.doConnect();
    }, 5000);
  }

  disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.onUpdate = null;
    this.ws?.close();
    this.ws = null;
  }
}
