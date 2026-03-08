import { useEffect } from 'react';
import { useAlertStore } from '../stores/alertStore';

export function useAlerts() {
  const store = useAlertStore();

  useEffect(() => {
    store.initialize();
  }, []);

  return {
    alerts: store.alerts,
    unreadCount: store.unreadCount,
    isLoading: store.isLoading,
    isRefreshing: store.isRefreshing,
    error: store.error,
    hasMore: store.hasMore,
    refresh: store.refresh,
    loadMore: store.loadMore,
    markAsRead: store.markAsRead,
    markAllAsRead: store.markAllAsRead,
    fetchUnreadCount: store.fetchUnreadCount,
  };
}
