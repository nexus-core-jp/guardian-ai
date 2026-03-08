import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import * as SecureStore from 'expo-secure-store';
import { API_URL } from '../constants';
import type {
  LoginResponse,
  User,
  Child,
  School,
  SafeRoute,
  Alert,
  DangerZone,
  DangerReport,
  OnboardingRequest,
  ChildLocation,
  NotificationPreferences,
} from '../types';

const api = axios.create({
  baseURL: API_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use(async (config: InternalAxiosRequestConfig) => {
  const token = await SecureStore.getItemAsync('accessToken');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      try {
        const refreshToken = await SecureStore.getItemAsync('refreshToken');
        if (refreshToken) {
          const { data } = await axios.post<{ accessToken: string; refreshToken: string }>(
            `${API_URL}/auth/refresh`,
            { refreshToken }
          );
          await SecureStore.setItemAsync('accessToken', data.accessToken);
          await SecureStore.setItemAsync('refreshToken', data.refreshToken);
          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${data.accessToken}`;
          }
          return api(originalRequest);
        }
      } catch {
        await SecureStore.deleteItemAsync('accessToken');
        await SecureStore.deleteItemAsync('refreshToken');
        await SecureStore.deleteItemAsync('user');
      }
    }

    const message = getErrorMessage(error);
    return Promise.reject(new Error(message));
  }
);

function getErrorMessage(error: AxiosError): string {
  if (!error.response) {
    return 'ネットワークエラーが発生しました。接続を確認してください。';
  }
  switch (error.response.status) {
    case 400:
      return '入力内容に誤りがあります。';
    case 401:
      return 'ログインが必要です。';
    case 403:
      return 'アクセス権限がありません。';
    case 404:
      return 'データが見つかりませんでした。';
    case 429:
      return 'リクエストが多すぎます。しばらくお待ちください。';
    case 500:
      return 'サーバーエラーが発生しました。しばらくお待ちください。';
    default:
      return 'エラーが発生しました。もう一度お試しください。';
  }
}

// Auth
export const authApi = {
  loginWithLine: (code: string, redirectUri: string) =>
    api.post<LoginResponse>('/auth/line', { code, redirectUri }).then((r) => r.data),

  loginWithApple: (identityToken: string) =>
    api.post<LoginResponse>('/auth/apple', { identityToken }).then((r) => r.data),

  loginWithGoogle: (idToken: string) =>
    api.post<LoginResponse>('/auth/google', { idToken }).then((r) => r.data),

  getMe: () => api.get<User>('/auth/me').then((r) => r.data),

  logout: () => api.post('/auth/logout'),
};

// Onboarding
export const onboardingApi = {
  complete: (data: OnboardingRequest) =>
    api.post<{ success: boolean }>('/onboarding/complete', data).then((r) => r.data),
};

// Children
export const childrenApi = {
  list: () => api.get<Child[]>('/children').then((r) => r.data),

  get: (id: string) => api.get<Child>(`/children/${id}`).then((r) => r.data),

  update: (id: string, data: Partial<Child>) =>
    api.patch<Child>(`/children/${id}`, data).then((r) => r.data),

  getLocation: (id: string) =>
    api.get<ChildLocation>(`/children/${id}/location`).then((r) => r.data),

  getLocationHistory: (id: string, date: string) =>
    api.get<ChildLocation[]>(`/children/${id}/location/history`, { params: { date } }).then((r) => r.data),
};

// Schools
export const schoolsApi = {
  search: (query: string, lat?: number, lng?: number) =>
    api
      .get<School[]>('/schools/search', { params: { q: query, lat, lng } })
      .then((r) => r.data),

  nearby: (lat: number, lng: number, radius?: number) =>
    api
      .get<School[]>('/schools/nearby', { params: { lat, lng, radius: radius || 5000 } })
      .then((r) => r.data),
};

// Routes
export const routesApi = {
  getSafeRoute: (childId: string) =>
    api.get<SafeRoute>(`/routes/safe/${childId}`).then((r) => r.data),

  calculateRoute: (homeLatLng: { lat: number; lng: number }, schoolLatLng: { lat: number; lng: number }) =>
    api
      .post<SafeRoute>('/routes/calculate', {
        homeLat: homeLatLng.lat,
        homeLng: homeLatLng.lng,
        schoolLat: schoolLatLng.lat,
        schoolLng: schoolLatLng.lng,
      })
      .then((r) => r.data),
};

// Alerts
export const alertsApi = {
  list: (page: number = 1, limit: number = 20) =>
    api.get<{ alerts: Alert[]; total: number }>('/alerts', { params: { page, limit } }).then((r) => r.data),

  markRead: (id: string) => api.patch(`/alerts/${id}/read`).then((r) => r.data),

  markAllRead: () => api.patch('/alerts/read-all').then((r) => r.data),

  getUnreadCount: () =>
    api.get<{ count: number }>('/alerts/unread-count').then((r) => r.data),
};

// Danger Zones / Community
export const communityApi = {
  getDangerZones: (lat: number, lng: number, radius?: number) =>
    api
      .get<DangerZone[]>('/community/danger-zones', { params: { lat, lng, radius: radius || 3000 } })
      .then((r) => r.data),

  reportDanger: (report: DangerReport) =>
    api.post<DangerZone>('/community/danger-zones', report).then((r) => r.data),

  confirmDanger: (id: string) =>
    api.post<{ confirmed: boolean }>(`/community/danger-zones/${id}/confirm`).then((r) => r.data),
};

// Notifications
export const notificationsApi = {
  registerPushToken: (token: string, platform: 'ios' | 'android') =>
    api.post('/notifications/register', { token, platform }).then((r) => r.data),

  getPreferences: () =>
    api.get<NotificationPreferences>('/notifications/preferences').then((r) => r.data),

  updatePreferences: (prefs: Partial<NotificationPreferences>) =>
    api.patch<NotificationPreferences>('/notifications/preferences', prefs).then((r) => r.data),
};

// Settings
export const settingsApi = {
  updateProfile: (data: { name?: string; email?: string }) =>
    api.patch<User>('/settings/profile', data).then((r) => r.data),

  updateHomeLocation: (lat: number, lng: number, address: string) =>
    api.patch('/settings/home-location', { latitude: lat, longitude: lng, address }).then((r) => r.data),

  deleteAccount: () => api.delete('/settings/account').then((r) => r.data),
};

export default api;
