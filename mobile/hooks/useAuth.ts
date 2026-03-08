import { useEffect } from 'react';
import { useAuthStore } from '../stores/authStore';
import { refreshSession } from '../services/auth';

export function useAuth() {
  const {
    user,
    isAuthenticated,
    isLoading,
    isOnboarded,
    loadStoredAuth,
    logout,
  } = useAuthStore();

  useEffect(() => {
    loadStoredAuth();
  }, [loadStoredAuth]);

  useEffect(() => {
    if (isAuthenticated) {
      refreshSession();
    }
  }, [isAuthenticated]);

  return {
    user,
    isAuthenticated,
    isLoading,
    isOnboarded,
    logout,
  };
}
