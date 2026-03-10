import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { getItem, setItem, deleteItem } from './storage';
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
  const token = await getItem('accessToken');
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
        const refreshToken = await getItem('refreshToken');
        if (refreshToken) {
          const { data } = await axios.post<{ access_token: string; refresh_token: string }>(
            `${API_URL}/auth/refresh`,
            { refresh_token: refreshToken }
          );
          await setItem('accessToken', data.access_token);
          await setItem('refreshToken', data.refresh_token);
          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
          }
          return api(originalRequest);
        }
      } catch {
        await deleteItem('accessToken');
        await deleteItem('refreshToken');
        await deleteItem('user');
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
    api.post<LoginResponse>('/auth/line', { code, redirect_uri: redirectUri }).then((r) => r.data),

  // 開発用: JWTトークンで直接ログイン
  devLogin: (token: string) => {
    return api.get<User>('/auth/me', {
      headers: { Authorization: `Bearer ${token}` },
    }).then((r) => r.data);
  },

  getMe: () => api.get<User>('/auth/me').then((r) => r.data),

  logout: () => api.post('/auth/logout').then((r) => r.data),
};

// Onboarding
export const onboardingApi = {
  complete: (data: OnboardingRequest) =>
    api.post('/auth/onboarding', {
      home_latitude: data.homeLatitude,
      home_longitude: data.homeLongitude,
      school_name: data.schoolName,
      school_id: data.schoolId,
      child_name: data.childName,
      child_grade: data.childGrade,
    }).then((r) => r.data),
};

// Children
export const childrenApi = {
  list: () => api.get<{ children: Child[]; total: number }>('/children').then((r) => r.data),

  get: (id: string) => api.get<Child>(`/children/${id}`).then((r) => r.data),

  update: (id: string, data: Partial<Child>) =>
    api.put<Child>(`/children/${id}`, data).then((r) => r.data),

  getLocation: (id: string) =>
    api.get<ChildLocation>(`/locations/${id}/latest`).then((r) => r.data),

  getLocationHistory: (id: string, params?: { limit?: number }) =>
    api.get<ChildLocation[]>(`/locations/${id}/history`, { params }).then((r) => r.data),
};

// Schools
export const schoolsApi = {
  search: (query: string, lat?: number, lng?: number) =>
    api
      .get<{ schools: School[]; total: number }>('/schools/search', { params: { q: query, lat, lng } })
      .then((r) => r.data),

  nearby: (lat: number, lng: number, limit?: number) =>
    api
      .get<{ schools: School[]; total: number }>('/schools/nearby', { params: { lat, lng, limit: limit || 10 } })
      .then((r) => r.data),
};

// Routes
export const routesApi = {
  getRecommended: (childId: string) =>
    api.get<SafeRoute>(`/routes/${childId}/recommended`).then((r) => r.data),

  list: (childId: string) =>
    api.get<{ routes: SafeRoute[]; total: number }>(`/routes/${childId}`).then((r) => r.data),

  calculate: (data: {
    origin: { latitude: number; longitude: number };
    destination: { latitude: number; longitude: number };
    child_id?: string;
  }) =>
    api.post<SafeRoute>('/routes/calculate', data).then((r) => r.data),
};

// Alerts
export const alertsApi = {
  list: (page: number = 1, limit: number = 20) =>
    api.get<{ alerts: Alert[]; total: number; unread_count: number }>('/alerts', { params: { skip: (page - 1) * limit, limit } }).then((r) => r.data),

  markRead: (id: string) => api.put(`/alerts/${id}/read`).then((r) => r.data),

  markAllRead: () => api.put('/alerts/read-all').then((r) => r.data),

  getUnreadCount: () =>
    api.get<{ unread_count: number }>('/alerts/unread').then((r) => r.data),
};

// Danger Zones / Community
export const communityApi = {
  getDangerZones: (lat: number, lng: number, radius?: number) =>
    api
      .get<{ danger_zones: DangerZone[]; total: number }>('/community/dangers', { params: { latitude: lat, longitude: lng, radius: radius || 3000 } })
      .then((r) => r.data),

  reportDanger: (report: DangerReport) =>
    api.post<DangerZone>('/community/dangers', {
      latitude: report.latitude,
      longitude: report.longitude,
      risk_type: report.type,
      risk_level: report.riskLevel || 5,
      title: report.title,
      description: report.description,
    }).then((r) => r.data),

  confirmDanger: (zoneId: string) =>
    api.post<DangerZone>(`/community/dangers/${zoneId}/confirm`).then((r) => r.data),

  getHeatmap: (lat: number, lng: number, radius?: number) =>
    api.get('/community/heatmap', { params: { latitude: lat, longitude: lng, radius: radius || 3000 } }).then((r) => r.data),
};

// Notifications
export const notificationsApi = {
  registerPushToken: (token: string, _platform: 'ios' | 'android') =>
    api.put('/auth/fcm-token', null, { params: { fcm_token: token } }).then((r) => r.data),

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
