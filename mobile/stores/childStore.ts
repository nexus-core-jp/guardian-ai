import { create } from 'zustand';
import { childrenApi } from '../services/api';
import type { Child } from '../types';

interface ChildState {
  children: Child[];
  activeChildId: string | undefined;
  isLoading: boolean;
  initialized: boolean;

  fetchChildren: () => Promise<void>;
  setActiveChild: (id: string) => void;
  initialize: () => void;
}

export const useChildStore = create<ChildState>((set, get) => ({
  children: [],
  activeChildId: undefined,
  isLoading: false,
  initialized: false,

  fetchChildren: async () => {
    set({ isLoading: true });
    try {
      const data = await childrenApi.list();
      set({
        children: data.children,
        activeChildId: data.children.length > 0 ? data.children[0].id : undefined,
      });
    } catch {
      // Silently fail
    } finally {
      set({ isLoading: false });
    }
  },

  setActiveChild: (id) => set({ activeChildId: id }),

  initialize: () => {
    const { initialized, fetchChildren } = get();
    if (!initialized) {
      set({ initialized: true });
      fetchChildren();
    }
  },
}));
