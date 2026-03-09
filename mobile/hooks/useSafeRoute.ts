import { useEffect, useState, useCallback } from 'react';
import { routesApi } from '../services/api';
import type { SafeRoute } from '../types';

export function useSafeRoute(childId: string | undefined) {
  const [route, setRoute] = useState<SafeRoute | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchRoute = useCallback(async () => {
    if (!childId) {
      setIsLoading(false);
      return;
    }
    try {
      setIsLoading(true);
      setError(null);
      const data = await routesApi.getRecommended(childId);
      setRoute(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'ルート情報を取得できませんでした');
    } finally {
      setIsLoading(false);
    }
  }, [childId]);

  useEffect(() => {
    fetchRoute();
  }, [fetchRoute]);

  return { route, isLoading, error, refresh: fetchRoute };
}
