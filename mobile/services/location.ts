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

/**
 * WebSocketメッセージの型定義
 */
interface WSLocationUpdate {
  type: 'location_update';
  child_id: string;
  data: {
    id: string;
    child_id: string;
    latitude: number;
    longitude: number;
    speed?: number;
    accuracy?: number;
    battery_level?: number;
    source: string;
    timestamp: string;
  };
}

interface WSAlert {
  type: 'alert';
  data: {
    id: string;
    alert_type: string;
    severity: string;
    title: string;
    message: string;
    child_id: string;
    latitude?: number;
    longitude?: number;
  };
}

interface WSSubscribed {
  type: 'subscribed' | 'unsubscribed';
  child_id: string;
}

interface WSPong {
  type: 'pong';
}

interface WSError {
  type: 'error';
  message: string;
}

type WSMessage = WSLocationUpdate | WSAlert | WSSubscribed | WSPong | WSError;

export class ChildLocationSocket {
  private ws: WebSocket | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private pingTimer: ReturnType<typeof setInterval> | null = null;
  private onLocationUpdate: ((location: ChildLocation) => void) | null = null;
  private onAlertReceived: ((alert: WSAlert['data']) => void) | null = null;
  private childId: string;
  private token: string;
  private isConnecting = false;

  constructor(childId: string, token: string) {
    this.childId = childId;
    this.token = token;
  }

  connect(
    onLocationUpdate: (location: ChildLocation) => void,
    onAlertReceived?: (alert: WSAlert['data']) => void,
  ): void {
    this.onLocationUpdate = onLocationUpdate;
    this.onAlertReceived = onAlertReceived ?? null;
    this.doConnect();
  }

  private doConnect(): void {
    if (this.isConnecting) return;
    this.isConnecting = true;

    try {
      // バックエンドの新しいWebSocketエンドポイント形式
      const wsUrl = `${WS_URL}/api/v1/ws?token=${encodeURIComponent(this.token)}`;
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        this.isConnecting = false;
        console.log('WebSocket connected');

        // 子どもの位置情報を購読
        this.send({ action: 'subscribe', child_id: this.childId });

        // Pingで接続を維持（30秒間隔）
        this.startPing();
      };

      this.ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data) as WSMessage;
          this.handleMessage(msg);
        } catch {
          console.warn('Failed to parse WebSocket message');
        }
      };

      this.ws.onclose = () => {
        this.isConnecting = false;
        this.stopPing();
        this.scheduleReconnect();
      };

      this.ws.onerror = () => {
        this.isConnecting = false;
        this.ws?.close();
      };
    } catch {
      this.isConnecting = false;
      this.scheduleReconnect();
    }
  }

  private handleMessage(msg: WSMessage): void {
    switch (msg.type) {
      case 'location_update': {
        const data = msg.data;
        // バックエンドのLocationResponseをChildLocation形式に変換
        const childLocation: ChildLocation = {
          childId: data.child_id,
          childName: '', // REST APIから取得済みの名前を使用
          location: {
            latitude: data.latitude,
            longitude: data.longitude,
            accuracy: data.accuracy,
            timestamp: data.timestamp,
            source: data.source as 'gps_device' | 'app' | 'manual',
          },
          status: 'moving',
          statusLabel: '移動中',
          batteryLevel: data.battery_level,
        };
        this.onLocationUpdate?.(childLocation);
        break;
      }

      case 'alert':
        this.onAlertReceived?.(msg.data);
        break;

      case 'subscribed':
        console.log(`Subscribed to child: ${msg.child_id}`);
        break;

      case 'pong':
        // Ping応答 — 接続維持確認
        break;

      case 'error':
        console.warn(`WebSocket error: ${msg.message}`);
        break;
    }
  }

  private send(data: Record<string, string>): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  private startPing(): void {
    this.stopPing();
    this.pingTimer = setInterval(() => {
      this.send({ action: 'ping' });
    }, 30000);
  }

  private stopPing(): void {
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
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
    this.stopPing();
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    // 購読解除メッセージを送信
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.send({ action: 'unsubscribe', child_id: this.childId });
    }
    this.onLocationUpdate = null;
    this.onAlertReceived = null;
    this.ws?.close();
    this.ws = null;
  }
}
