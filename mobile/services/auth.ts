import * as AuthSession from 'expo-auth-session';
import * as WebBrowser from 'expo-web-browser';
import * as Crypto from 'expo-crypto';
import { LINE_CLIENT_ID, LINE_REDIRECT_URI } from '../constants';
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
    const response = await authApi.loginWithLine(result.params.code, redirectUri);
    await useAuthStore.getState().login(response.user, response.accessToken, response.refreshToken);
    return response;
  }

  return null;
}

export async function loginWithApple(): Promise<LoginResponse | null> {
  // Apple Sign-In will be integrated using expo-apple-authentication
  // For now, return null as placeholder
  console.log('Apple login not yet implemented');
  return null;
}

export async function loginWithGoogle(): Promise<LoginResponse | null> {
  // Google Sign-In will be integrated using expo-auth-session with Google provider
  // For now, return null as placeholder
  console.log('Google login not yet implemented');
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
