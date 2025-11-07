/**
 * Zustand Store for Global State Management
 * Handles tenant context, user state, and UI state
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'member' | 'viewer';
  tenant_id: string;
}

interface Tenant {
  id: string;
  slug: string;
  name: string;
  plan: 'starter' | 'professional' | 'enterprise';
}

interface UploadProgress {
  fileName: string;
  progress: number;
  status: 'uploading' | 'processing' | 'completed' | 'failed';
  evfId?: string;
  error?: string;
}

interface AppState {
  // User & Auth
  user: User | null;
  tenant: Tenant | null;
  isAuthenticated: boolean;
  setUser: (user: User | null) => void;
  setTenant: (tenant: Tenant | null) => void;
  logout: () => void;

  // UI State
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;

  // Upload State
  uploads: Record<string, UploadProgress>;
  addUpload: (id: string, upload: UploadProgress) => void;
  updateUpload: (id: string, update: Partial<UploadProgress>) => void;
  removeUpload: (id: string) => void;

  // Notifications
  notifications: Array<{
    id: string;
    type: 'info' | 'success' | 'warning' | 'error';
    title: string;
    message: string;
    timestamp: number;
  }>;
  addNotification: (notification: Omit<AppState['notifications'][0], 'id' | 'timestamp'>) => void;
  removeNotification: (id: string) => void;
}

export const useStore = create<AppState>()(
  persist(
    (set, get) => ({
      // Initial state
      user: null,
      tenant: null,
      isAuthenticated: false,
      sidebarOpen: true,
      uploads: {},
      notifications: [],

      // Actions
      setUser: (user) => set({ user, isAuthenticated: !!user }),
      setTenant: (tenant) => set({ tenant }),

      logout: () => {
        set({
          user: null,
          tenant: null,
          isAuthenticated: false,
          uploads: {},
        });
      },

      setSidebarOpen: (open) => set({ sidebarOpen: open }),
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),

      addUpload: (id, upload) => {
        set((state) => ({
          uploads: {
            ...state.uploads,
            [id]: upload,
          },
        }));
      },

      updateUpload: (id, update) => {
        set((state) => ({
          uploads: {
            ...state.uploads,
            [id]: {
              ...state.uploads[id],
              ...update,
            },
          },
        }));
      },

      removeUpload: (id) => {
        set((state) => {
          const { [id]: removed, ...rest } = state.uploads;
          return { uploads: rest };
        });
      },

      addNotification: (notification) => {
        const id = Math.random().toString(36).slice(2);
        set((state) => ({
          notifications: [
            ...state.notifications,
            {
              ...notification,
              id,
              timestamp: Date.now(),
            },
          ],
        }));

        // Auto-remove after 5 seconds
        setTimeout(() => {
          get().removeNotification(id);
        }, 5000);
      },

      removeNotification: (id) => {
        set((state) => ({
          notifications: state.notifications.filter((n) => n.id !== id),
        }));
      },
    }),
    {
      name: 'evf-storage',
      partialize: (state) => ({
        user: state.user,
        tenant: state.tenant,
        isAuthenticated: state.isAuthenticated,
        sidebarOpen: state.sidebarOpen,
      }),
    }
  )
);
