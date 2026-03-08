import React, { useEffect } from 'react';
import { Stack, Redirect } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useAuth } from '../hooks/useAuth';
import {
  registerForPushNotifications,
  addNotificationReceivedListener,
  addNotificationResponseListener,
} from '../services/notifications';
import { router } from 'expo-router';

export default function RootLayout() {
  const { isAuthenticated, isLoading, isOnboarded } = useAuth();

  useEffect(() => {
    if (isAuthenticated) {
      registerForPushNotifications();

      const receivedSub = addNotificationReceivedListener((notification) => {
        console.log('Notification received:', notification.request.content.title);
      });

      const responseSub = addNotificationResponseListener((response) => {
        const data = response.notification.request.content.data;
        if (data?.type === 'alert') {
          router.push('/(main)/alerts');
        }
      });

      return () => {
        receivedSub.remove();
        responseSub.remove();
      };
    }
  }, [isAuthenticated]);

  if (isLoading) {
    // Show splash / index screen while loading
    return (
      <>
        <StatusBar style="dark" />
        <Stack screenOptions={{ headerShown: false, animation: 'fade' }}>
          <Stack.Screen name="index" />
        </Stack>
      </>
    );
  }

  if (!isAuthenticated) {
    return (
      <>
        <StatusBar style="dark" />
        <Stack screenOptions={{ headerShown: false, animation: 'fade' }}>
          <Stack.Screen name="index" redirect />
          <Stack.Screen name="(auth)" />
          <Stack.Screen name="(onboarding)" redirect />
          <Stack.Screen name="(main)" redirect />
        </Stack>
        <Redirect href="/(auth)/login" />
      </>
    );
  }

  if (!isOnboarded) {
    return (
      <>
        <StatusBar style="dark" />
        <Stack screenOptions={{ headerShown: false, animation: 'fade' }}>
          <Stack.Screen name="index" redirect />
          <Stack.Screen name="(auth)" redirect />
          <Stack.Screen name="(onboarding)" />
          <Stack.Screen name="(main)" redirect />
        </Stack>
        <Redirect href="/(onboarding)/home-location" />
      </>
    );
  }

  return (
    <>
      <StatusBar style="dark" />
      <Stack screenOptions={{ headerShown: false, animation: 'fade' }}>
        <Stack.Screen name="index" redirect />
        <Stack.Screen name="(auth)" redirect />
        <Stack.Screen name="(onboarding)" redirect />
        <Stack.Screen name="(main)" />
      </Stack>
      <Redirect href="/(main)/map" />
    </>
  );
}
