import React, { useEffect } from 'react';
import { Stack } from 'expo-router';
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

  useEffect(() => {
    if (isLoading) return;

    if (!isAuthenticated) {
      router.replace('/(auth)/login');
    } else if (!isOnboarded) {
      router.replace('/(onboarding)/home-location');
    } else {
      router.replace('/(main)/map');
    }
  }, [isAuthenticated, isLoading, isOnboarded]);

  return (
    <>
      <StatusBar style="dark" />
      <Stack screenOptions={{ headerShown: false, animation: 'fade' }}>
        <Stack.Screen name="index" />
        <Stack.Screen name="(auth)" />
        <Stack.Screen name="(onboarding)" />
        <Stack.Screen name="(main)" />
      </Stack>
    </>
  );
}
