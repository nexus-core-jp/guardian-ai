import { Platform } from 'react-native';
import { notificationsApi } from './api';

// Web ではプッシュ通知APIを使わない
const isNative = Platform.OS !== 'web';

let Notifications: typeof import('expo-notifications') | null = null;
let Device: typeof import('expo-device') | null = null;
let Constants: typeof import('expo-constants').default | null = null;

if (isNative) {
  Notifications = require('expo-notifications');
  Device = require('expo-device');
  Constants = require('expo-constants').default;

  Notifications.setNotificationHandler({
    handleNotification: async () => ({
      shouldShowAlert: true,
      shouldPlaySound: true,
      shouldSetBadge: true,
      shouldShowBanner: true,
      shouldShowList: true,
    }),
  });
}

// ダミーのサブスクリプション（Web用）
const dummySubscription = { remove: () => {} };

export async function registerForPushNotifications(): Promise<string | null> {
  if (!isNative || !Notifications || !Device || !Constants) return null;

  if (!Device.isDevice) {
    console.log('Push notifications require a physical device');
    return null;
  }

  const { status: existingStatus } = await Notifications.getPermissionsAsync();
  let finalStatus = existingStatus;

  if (existingStatus !== 'granted') {
    const { status } = await Notifications.requestPermissionsAsync();
    finalStatus = status;
  }

  if (finalStatus !== 'granted') {
    return null;
  }

  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('default', {
      name: '通知',
      importance: Notifications.AndroidImportance.HIGH,
      vibrationPattern: [0, 250, 250, 250],
      lightColor: '#4A90D9',
    });

    await Notifications.setNotificationChannelAsync('alerts', {
      name: '緊急アラート',
      importance: Notifications.AndroidImportance.MAX,
      vibrationPattern: [0, 500, 250, 500],
      lightColor: '#FF3B30',
    });
  }

  try {
    const tokenData = await Notifications.getExpoPushTokenAsync({
      projectId: Constants.expoConfig?.extra?.eas?.projectId,
    });
    const token = tokenData.data;

    await notificationsApi.registerPushToken(
      token,
      Platform.OS as 'ios' | 'android'
    );

    return token;
  } catch (error) {
    console.error('Failed to get push token:', error);
    return null;
  }
}

export function addNotificationReceivedListener(
  handler: (notification: any) => void
): { remove: () => void } {
  if (!isNative || !Notifications) return dummySubscription;
  return Notifications.addNotificationReceivedListener(handler);
}

export function addNotificationResponseListener(
  handler: (response: any) => void
): { remove: () => void } {
  if (!isNative || !Notifications) return dummySubscription;
  return Notifications.addNotificationResponseReceivedListener(handler);
}

export async function getBadgeCount(): Promise<number> {
  if (!isNative || !Notifications) return 0;
  return Notifications.getBadgeCountAsync();
}

export async function setBadgeCount(count: number): Promise<void> {
  if (!isNative || !Notifications) return;
  await Notifications.setBadgeCountAsync(count);
}
