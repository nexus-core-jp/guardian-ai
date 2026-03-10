import { useAuthStore } from '../../stores/authStore';
import { setItem, deleteItem, getItem } from '../../services/storage';
import type { User } from '../../types';

jest.mock('../../services/storage', () => ({
  getItem: jest.fn(),
  setItem: jest.fn().mockResolvedValue(undefined),
  deleteItem: jest.fn().mockResolvedValue(undefined),
}));

const mockUser: User = {
  id: 'test-uuid',
  name: 'テスト保護者',
  email: 'test@example.com',
  lineId: null,
  avatarUrl: null,
  onboardingCompleted: false,
  createdAt: '2026-01-01T00:00:00Z',
  updatedAt: '2026-01-01T00:00:00Z',
};

describe('authStore', () => {
  beforeEach(() => {
    // ストアをリセット
    useAuthStore.setState({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: true,
      isOnboarded: false,
    });
    jest.clearAllMocks();
  });

  it('初期状態が正しい', () => {
    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.isAuthenticated).toBe(false);
    expect(state.isLoading).toBe(true);
  });

  it('login でユーザー情報とトークンを保存できる', async () => {
    await useAuthStore.getState().login(mockUser, 'access-123', 'refresh-456');

    const state = useAuthStore.getState();
    expect(state.user).toEqual(mockUser);
    expect(state.accessToken).toBe('access-123');
    expect(state.refreshToken).toBe('refresh-456');
    expect(state.isAuthenticated).toBe(true);
    expect(setItem).toHaveBeenCalledWith('accessToken', 'access-123');
    expect(setItem).toHaveBeenCalledWith('refreshToken', 'refresh-456');
  });

  it('logout でストレージとストアをクリアする', async () => {
    await useAuthStore.getState().login(mockUser, 'access-123', 'refresh-456');
    await useAuthStore.getState().logout();

    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.isAuthenticated).toBe(false);
    expect(deleteItem).toHaveBeenCalledWith('accessToken');
    expect(deleteItem).toHaveBeenCalledWith('refreshToken');
  });

  it('loadStoredAuth でストレージから復元できる', async () => {
    (getItem as jest.Mock).mockImplementation((key: string) => {
      switch (key) {
        case 'accessToken': return Promise.resolve('stored-access');
        case 'refreshToken': return Promise.resolve('stored-refresh');
        case 'user': return Promise.resolve(JSON.stringify(mockUser));
        default: return Promise.resolve(null);
      }
    });

    await useAuthStore.getState().loadStoredAuth();

    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(true);
    expect(state.user?.name).toBe('テスト保護者');
    expect(state.isLoading).toBe(false);
  });

  it('loadStoredAuth でトークンがない場合はisLoadingのみ更新', async () => {
    (getItem as jest.Mock).mockResolvedValue(null);

    await useAuthStore.getState().loadStoredAuth();

    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(false);
    expect(state.isLoading).toBe(false);
  });

  it('setOnboarded でオンボーディング状態を更新できる', async () => {
    await useAuthStore.getState().login(mockUser, 'a', 'r');
    useAuthStore.getState().setOnboarded(true);

    const state = useAuthStore.getState();
    expect(state.isOnboarded).toBe(true);
    expect(state.user?.onboardingCompleted).toBe(true);
  });

  it('setUser でユーザー情報を更新できる', () => {
    const updatedUser = { ...mockUser, name: '更新後の名前', onboardingCompleted: true };
    useAuthStore.getState().setUser(updatedUser);

    const state = useAuthStore.getState();
    expect(state.user?.name).toBe('更新後の名前');
    expect(state.isOnboarded).toBe(true);
  });
});
