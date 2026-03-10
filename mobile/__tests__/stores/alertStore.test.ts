import { useAlertStore } from '../../stores/alertStore';
import { alertsApi } from '../../services/api';

jest.mock('../../services/storage', () => ({
  getItem: jest.fn().mockResolvedValue(null),
  setItem: jest.fn().mockResolvedValue(undefined),
  deleteItem: jest.fn().mockResolvedValue(undefined),
}));

jest.mock('../../services/api', () => ({
  alertsApi: {
    list: jest.fn(),
    markRead: jest.fn(),
    markAllRead: jest.fn(),
    getUnreadCount: jest.fn(),
  },
}));

const mockAlerts = [
  {
    id: 'alert-1',
    type: 'route_deviation',
    severity: 'warning',
    title: 'ルート逸脱',
    message: 'テスト',
    childId: 'child-1',
    read: false,
    createdAt: '2026-01-01T00:00:00Z',
  },
  {
    id: 'alert-2',
    type: 'zone_entry',
    severity: 'critical',
    title: '危険エリア侵入',
    message: 'テスト2',
    childId: 'child-1',
    read: false,
    createdAt: '2026-01-01T01:00:00Z',
  },
];

describe('alertStore', () => {
  beforeEach(() => {
    useAlertStore.setState({
      alerts: [],
      unreadCount: 0,
      isLoading: true,
      isRefreshing: false,
      error: null,
      page: 1,
      hasMore: true,
      initialized: false,
    });
    jest.clearAllMocks();
  });

  it('fetchAlerts でアラート一覧を取得できる', async () => {
    (alertsApi.list as jest.Mock).mockResolvedValue({
      alerts: mockAlerts,
      total: 2,
      unread_count: 2,
    });

    await useAlertStore.getState().fetchAlerts(1);

    const state = useAlertStore.getState();
    expect(state.alerts).toHaveLength(2);
    expect(state.isLoading).toBe(false);
    expect(alertsApi.list).toHaveBeenCalledWith(1, 20);
  });

  it('fetchAlerts のエラーが正しく処理される', async () => {
    (alertsApi.list as jest.Mock).mockRejectedValue(new Error('ネットワークエラー'));

    await useAlertStore.getState().fetchAlerts(1);

    const state = useAlertStore.getState();
    expect(state.error).toBe('ネットワークエラー');
    expect(state.isLoading).toBe(false);
  });

  it('fetchUnreadCount で未読数を取得できる', async () => {
    (alertsApi.getUnreadCount as jest.Mock).mockResolvedValue({ unread_count: 5 });

    await useAlertStore.getState().fetchUnreadCount();

    expect(useAlertStore.getState().unreadCount).toBe(5);
  });

  it('markAsRead でアラートを既読にできる', async () => {
    useAlertStore.setState({ alerts: mockAlerts, unreadCount: 2 });
    (alertsApi.markRead as jest.Mock).mockResolvedValue({});

    await useAlertStore.getState().markAsRead('alert-1');

    const state = useAlertStore.getState();
    expect(state.alerts[0].read).toBe(true);
    expect(state.alerts[1].read).toBe(false);
    expect(state.unreadCount).toBe(1);
  });

  it('markAllAsRead で全アラートを既読にできる', async () => {
    useAlertStore.setState({ alerts: mockAlerts, unreadCount: 2 });
    (alertsApi.markAllRead as jest.Mock).mockResolvedValue({});

    await useAlertStore.getState().markAllAsRead();

    const state = useAlertStore.getState();
    expect(state.alerts.every((a) => a.read)).toBe(true);
    expect(state.unreadCount).toBe(0);
  });

  it('initialize は一度だけ fetchAlerts を呼ぶ', () => {
    (alertsApi.list as jest.Mock).mockResolvedValue({ alerts: [], total: 0, unread_count: 0 });
    (alertsApi.getUnreadCount as jest.Mock).mockResolvedValue({ unread_count: 0 });

    useAlertStore.getState().initialize();
    useAlertStore.getState().initialize();

    expect(alertsApi.list).toHaveBeenCalledTimes(1);
  });

  it('loadMore は次のページを取得する', () => {
    useAlertStore.setState({ hasMore: true, isLoading: false, page: 1 });
    (alertsApi.list as jest.Mock).mockResolvedValue({ alerts: [], total: 0, unread_count: 0 });

    useAlertStore.getState().loadMore();

    expect(alertsApi.list).toHaveBeenCalledWith(2, 20);
  });

  it('loadMore はhasMoreがfalseの場合に呼ばない', () => {
    useAlertStore.setState({ hasMore: false, isLoading: false, page: 1 });

    useAlertStore.getState().loadMore();

    expect(alertsApi.list).not.toHaveBeenCalled();
  });
});
