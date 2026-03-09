import { create } from 'zustand';
import { getItem, setItem, deleteItem } from '../services/storage';
import type { User } from '../types';

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isOnboarded: boolean;

  setUser: (user: User) => void;
  setTokens: (accessToken: string, refreshToken: string) => void;
  login: (user: User, accessToken: string, refreshToken: string) => Promise<void>;
  logout: () => Promise<void>;
  loadStoredAuth: () => Promise<void>;
  setOnboarded: (value: boolean) => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  accessToken: null,
  refreshToken: null,
  isAuthenticated: false,
  isLoading: true,
  isOnboarded: false,

  setUser: (user) => {
    set({ user, isOnboarded: user.onboardingCompleted });
  },

  setTokens: (accessToken, refreshToken) => {
    set({ accessToken, refreshToken });
  },

  login: async (user, accessToken, refreshToken) => {
    await setItem('accessToken', accessToken);
    await setItem('refreshToken', refreshToken);
    await setItem('user', JSON.stringify(user));
    set({
      user,
      accessToken,
      refreshToken,
      isAuthenticated: true,
      isOnboarded: user.onboardingCompleted,
    });
  },

  logout: async () => {
    await deleteItem('accessToken');
    await deleteItem('refreshToken');
    await deleteItem('user');
    set({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isOnboarded: false,
    });
  },

  loadStoredAuth: async () => {
    try {
      const accessToken = await getItem('accessToken');
      const refreshToken = await getItem('refreshToken');
      const userStr = await getItem('user');

      if (accessToken && refreshToken && userStr) {
        const user = JSON.parse(userStr) as User;
        set({
          user,
          accessToken,
          refreshToken,
          isAuthenticated: true,
          isOnboarded: user.onboardingCompleted,
          isLoading: false,
        });
      } else {
        set({ isLoading: false });
      }
    } catch {
      set({ isLoading: false });
    }
  },

  setOnboarded: (value) => {
    const { user } = get();
    if (user) {
      const updatedUser = { ...user, onboardingCompleted: value };
      setItem('user', JSON.stringify(updatedUser));
      set({ user: updatedUser, isOnboarded: value });
    }
  },
}));
