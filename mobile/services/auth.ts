import { Platform } from 'react-native';
import * as AuthSession from 'expo-auth-session';
import * as WebBrowser from 'expo-web-browser';
import * as Crypto from 'expo-crypto';
import { LINE_CLIENT_ID, LINE_REDIRECT_URI, GOOGLE_CLIENT_ID } from '../constants';
import { authApi } from './api';
import { useAuthStore } from '../stores/authStore';
import type { LoginResponse } from '../types';

WebBrowser.maybeCompleteAuthSession();

const LINE_AUTH_URL = 'https://access.line.me/oauth2/v2.1/authorize';
const LINE_TOKEN_URL = 'https://api.line.me/oauth2/v2.1/token';

const discovery: AuthSession.DiscoveryDocument = {
  authorizationEndpoint: LINE_AUTH_URL,
  tokenEndpoint: LINE_TOKEN_URL,
};

export async function loginWithLine(): Promise<LoginResponse | null> {
  const state = await Crypto.digestStringAsync(
    Crypto.CryptoDigestAlgorithm.SHA256,
    Math.random().toString()
  );

  const redirectUri = AuthSession.makeRedirectUri({ scheme: 'guardian-ai' });

  const request = new AuthSession.AuthRequest({
    clientId: LINE_CLIENT_ID,
    redirectUri,
    scopes: ['profile', 'openid', 'email'],
    responseType: AuthSession.ResponseType.Code,
    state,
    extraParams: {
      bot_prompt: 'normal',
    },
  });

  const result = await request.promptAsync(discovery);

  if (result.type === 'success' && result.params.code) {
    const raw = await authApi.loginWithLine(result.params.code, redirectUri);
    // バックエンドはsnake_case（access_token, refresh_token）で返す
    const response: LoginResponse = {
      accessToken: (raw as any).access_token ?? raw.accessToken,
      refreshToken: (raw as any).refresh_token ?? raw.refreshToken,
      user: raw.user,
    };
    await useAuthStore.getState().login(response.user, response.accessToken, response.refreshToken);
    return response;
  }

  return null;
}

export async function loginWithApple(): Promise<LoginResponse | null> {
  if (Platform.OS === 'web') {
    throw new Error('Apple Sign-InはiOSデバイスでのみ利用できます');
  }

  // expo-apple-authenticationを動的インポート（iOSのみ利用可能）
  const AppleAuthentication = require('expo-apple-authentication');

  const credential = await AppleAuthentication.signInAsync({
    requestedScopes: [
      AppleAuthentication.AppleAuthenticationScope.FULL_NAME,
      AppleAuthentication.AppleAuthenticationScope.EMAIL,
    ],
  });

  if (!credential.identityToken) {
    return null;
  }

  const fullName = credential.fullName
    ? [credential.fullName.familyName, credential.fullName.givenName]
        .filter(Boolean)
        .join(' ') || undefined
    : undefined;

  const raw = await authApi.loginWithApple(
    credential.identityToken,
    credential.authorizationCode ?? undefined,
    fullName,
  );

  const response: LoginResponse = {
    accessToken: (raw as any).access_token ?? raw.accessToken,
    refreshToken: (raw as any).refresh_token ?? raw.refreshToken,
    user: raw.user,
  };

  await useAuthStore.getState().login(response.user, response.accessToken, response.refreshToken);
  return response;
}

const GOOGLE_DISCOVERY: AuthSession.DiscoveryDocument = {
  authorizationEndpoint: 'https://accounts.google.com/o/oauth2/v2/auth',
  tokenEndpoint: 'https://oauth2.googleapis.com/token',
};

export async function loginWithGoogle(): Promise<LoginResponse | null> {
  if (!GOOGLE_CLIENT_ID) {
    throw new Error('Google Client IDが設定されていません');
  }

  const redirectUri = AuthSession.makeRedirectUri({ scheme: 'guardian-ai' });

  const request = new AuthSession.AuthRequest({
    clientId: GOOGLE_CLIENT_ID,
    redirectUri,
    scopes: ['openid', 'profile', 'email'],
    responseType: AuthSession.ResponseType.Token,
  });

  const result = await request.promptAsync(GOOGLE_DISCOVERY);

  if (result.type === 'success' && result.authentication?.accessToken) {
    // accessTokenからuserinfoを取得してid_tokenの代わりに使用
    // Google OAuth implicit flowではid_tokenが返される場合もある
    const idToken = (result.authentication as any).idToken || result.authentication.accessToken;

    const raw = await authApi.loginWithGoogle(idToken);

    const response: LoginResponse = {
      accessToken: (raw as any).access_token ?? raw.accessToken,
      refreshToken: (raw as any).refresh_token ?? raw.refreshToken,
      user: raw.user,
    };

    await useAuthStore.getState().login(response.user, response.accessToken, response.refreshToken);
    return response;
  }

  return null;
}

export async function refreshSession(): Promise<boolean> {
  try {
    const user = await authApi.getMe();
    useAuthStore.getState().setUser(user);
    return true;
  } catch {
    await useAuthStore.getState().logout();
    return false;
  }
}

export async function logoutUser(): Promise<void> {
  try {
    await authApi.logout();
  } catch {
    // Ignore network errors during logout
  } finally {
    await useAuthStore.getState().logout();
  }
}
