import { useEffect, useState, useRef, useCallback } from 'react';
import { useAuthStore } from '../stores/authStore';
import { useAlertStore } from '../stores/alertStore';
import { childrenApi } from '../services/api';
import { ChildLocationSocket } from '../services/location';
import type { ChildLocation } from '../types';

export function useChildLocation(childId: string | undefined) {
  const [location, setLocation] = useState<ChildLocation | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const socketRef = useRef<ChildLocationSocket | null>(null);
  const accessToken = useAuthStore((s) => s.accessToken);
  const fetchUnreadCount = useAlertStore((s) => s.fetchUnreadCount);

  const fetchLocation = useCallback(async () => {
    if (!childId) return;
    try {
      setIsLoading(true);
      setError(null);
      const data = await childrenApi.getLocation(childId);
      setLocation(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '位置情報を取得できませんでした');
    } finally {
      setIsLoading(false);
    }
  }, [childId]);

  useEffect(() => {
    fetchLocation();
  }, [fetchLocation]);

  useEffect(() => {
    if (!childId || !accessToken) return;

    const socket = new ChildLocationSocket(childId, accessToken);
    socketRef.current = socket;

    socket.connect(
      // 位置情報更新
      (data) => {
        // REST APIから取得した名前を保持
        setLocation((prev) => ({
          ...data,
          childName: prev?.childName || data.childName,
        }));
        setIsLoading(false);
      },
      // リアルタイムアラート受信
      (_alert) => {
        // アラートストアの未読カウントを更新
        fetchUnreadCount();
      },
    );

    return () => {
      socket.disconnect();
      socketRef.current = null;
    };
  }, [childId, accessToken, fetchUnreadCount]);

  return { location, isLoading, error, refresh: fetchLocation };
}
