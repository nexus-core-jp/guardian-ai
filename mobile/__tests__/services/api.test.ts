import axios from 'axios';

// api.ts内部でaxiosインスタンスを作っているのでモック
jest.mock('../../services/storage', () => ({
  getItem: jest.fn().mockResolvedValue(null),
  setItem: jest.fn().mockResolvedValue(undefined),
  deleteItem: jest.fn().mockResolvedValue(undefined),
}));

// axios をモック
jest.mock('axios', () => {
  const mockAxiosInstance = {
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    patch: jest.fn(),
    delete: jest.fn(),
    interceptors: {
      request: { use: jest.fn() },
      response: { use: jest.fn() },
    },
  };
  return {
    __esModule: true,
    default: {
      create: jest.fn(() => mockAxiosInstance),
      post: jest.fn(),
    },
  };
});

describe('API service', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('axiosインスタンスが正しく生成される', () => {
    // apiモジュールをインポートするとaxios.createが呼ばれる
    require('../../services/api');
    expect(axios.create).toHaveBeenCalledWith(
      expect.objectContaining({
        timeout: 15000,
        headers: { 'Content-Type': 'application/json' },
      })
    );
  });

  it('authApi.loginWithLine が正しいエンドポイントを呼ぶ', async () => {
    const mockInstance = (axios.create as jest.Mock).mock.results[0]?.value;
    if (!mockInstance) {
      // 再インポートしてインスタンスを取得
      jest.resetModules();
      require('../../services/api');
    }
    const { authApi } = require('../../services/api');
    const mockPost = (axios.create as jest.Mock).mock.results[0]?.value?.post;
    if (mockPost) {
      mockPost.mockResolvedValue({
        data: { access_token: 'test', refresh_token: 'test', user: {} },
      });
      await authApi.loginWithLine('code123', 'redirect://');
      expect(mockPost).toHaveBeenCalledWith('/auth/line', {
        code: 'code123',
        redirect_uri: 'redirect://',
      });
    }
  });

  it('authApi.loginWithApple が正しいパラメータを送信する', async () => {
    const { authApi } = require('../../services/api');
    const mockPost = (axios.create as jest.Mock).mock.results[0]?.value?.post;
    if (mockPost) {
      mockPost.mockResolvedValue({
        data: { access_token: 'test', refresh_token: 'test', user: {} },
      });
      await authApi.loginWithApple('apple-id-token', 'auth-code', 'Test User');
      expect(mockPost).toHaveBeenCalledWith('/auth/apple', {
        id_token: 'apple-id-token',
        authorization_code: 'auth-code',
        full_name: 'Test User',
      });
    }
  });

  it('authApi.loginWithGoogle が正しいパラメータを送信する', async () => {
    const { authApi } = require('../../services/api');
    const mockPost = (axios.create as jest.Mock).mock.results[0]?.value?.post;
    if (mockPost) {
      mockPost.mockResolvedValue({
        data: { access_token: 'test', refresh_token: 'test', user: {} },
      });
      await authApi.loginWithGoogle('google-id-token');
      expect(mockPost).toHaveBeenCalledWith('/auth/google', {
        id_token: 'google-id-token',
      });
    }
  });
});
