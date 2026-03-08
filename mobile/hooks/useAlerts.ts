import { useEffect, useState, useCallback } from 'react';
import { alertsApi } from '../services/api';
import type { Alert } from '../types';

export function useAlerts() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);

  const fetchAlerts = useCallback(async (pageNum: number = 1, refresh: boolean = false) => {
    try {
      if (refresh) setIsRefreshing(true);
      else if (pageNum === 1) setIsLoading(true);

      setError(null);
      const data = await alertsApi.list(pageNum, 20);

      if (refresh || pageNum === 1) {
        setAlerts(data.alerts);
      } else {
        setAlerts((prev) => [...prev, ...data.alerts]);
      }

      setHasMore(data.alerts.length === 20);
      setPage(pageNum);
    } catch (err) {
      setError(err instanceof Error ? err.message : '通知を取得できませんでした');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  const fetchUnreadCount = useCallback(async () => {
    try {
      const data = await alertsApi.getUnreadCount();
      setUnreadCount(data.count);
    } catch {
      // Silently fail
    }
  }, []);

  const markAsRead = useCallback(async (id: string) => {
    try {
      await alertsApi.markRead(id);
      setAlerts((prev) =>
        prev.map((a) => (a.id === id ? { ...a, read: true } : a))
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch {
      // Silently fail
    }
  }, []);

  const markAllAsRead = useCallback(async () => {
    try {
      await alertsApi.markAllRead();
      setAlerts((prev) => prev.map((a) => ({ ...a, read: true })));
      setUnreadCount(0);
    } catch {
      // Silently fail
    }
  }, []);

  const refresh = useCallback(() => fetchAlerts(1, true), [fetchAlerts]);
  const loadMore = useCallback(() => {
    if (hasMore && !isLoading) {
      fetchAlerts(page + 1);
    }
  }, [fetchAlerts, hasMore, isLoading, page]);

  useEffect(() => {
    fetchAlerts(1);
    fetchUnreadCount();
  }, [fetchAlerts, fetchUnreadCount]);

  return {
    alerts,
    unreadCount,
    isLoading,
    isRefreshing,
    error,
    hasMore,
    refresh,
    loadMore,
    markAsRead,
    markAllAsRead,
    fetchUnreadCount,
  };
}
