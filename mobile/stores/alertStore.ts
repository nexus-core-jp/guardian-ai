import { create } from 'zustand';
import { alertsApi } from '../services/api';
import type { Alert } from '../types';

interface AlertState {
  alerts: Alert[];
  unreadCount: number;
  isLoading: boolean;
  isRefreshing: boolean;
  error: string | null;
  page: number;
  hasMore: boolean;
  initialized: boolean;

  fetchAlerts: (pageNum?: number, refresh?: boolean) => Promise<void>;
  fetchUnreadCount: () => Promise<void>;
  markAsRead: (id: string) => Promise<void>;
  markAllAsRead: () => Promise<void>;
  refresh: () => Promise<void>;
  loadMore: () => void;
  initialize: () => void;
}

export const useAlertStore = create<AlertState>((set, get) => ({
  alerts: [],
  unreadCount: 0,
  isLoading: true,
  isRefreshing: false,
  error: null,
  page: 1,
  hasMore: true,
  initialized: false,

  fetchAlerts: async (pageNum: number = 1, refresh: boolean = false) => {
    try {
      if (refresh) set({ isRefreshing: true });
      else if (pageNum === 1) set({ isLoading: true });

      set({ error: null });
      const data = await alertsApi.list(pageNum, 20);

      if (refresh || pageNum === 1) {
        set({ alerts: data.alerts });
      } else {
        set((state) => ({ alerts: [...state.alerts, ...data.alerts] }));
      }

      set({ hasMore: data.alerts.length === 20, page: pageNum });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : '通知を取得できませんでした' });
    } finally {
      set({ isLoading: false, isRefreshing: false });
    }
  },

  fetchUnreadCount: async () => {
    try {
      const data = await alertsApi.getUnreadCount();
      set({ unreadCount: data.unread_count });
    } catch {
      // Silently fail
    }
  },

  markAsRead: async (id: string) => {
    try {
      await alertsApi.markRead(id);
      set((state) => ({
        alerts: state.alerts.map((a) => (a.id === id ? { ...a, read: true } : a)),
        unreadCount: Math.max(0, state.unreadCount - 1),
      }));
    } catch {
      // Silently fail
    }
  },

  markAllAsRead: async () => {
    try {
      await alertsApi.markAllRead();
      set((state) => ({
        alerts: state.alerts.map((a) => ({ ...a, read: true })),
        unreadCount: 0,
      }));
    } catch {
      // Silently fail
    }
  },

  refresh: async () => {
    await get().fetchAlerts(1, true);
  },

  loadMore: () => {
    const { hasMore, isLoading, page, fetchAlerts } = get();
    if (hasMore && !isLoading) {
      fetchAlerts(page + 1);
    }
  },

  initialize: () => {
    const { initialized, fetchAlerts, fetchUnreadCount } = get();
    if (!initialized) {
      set({ initialized: true });
      fetchAlerts(1);
      fetchUnreadCount();
    }
  },
}));
