import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Switch,
  Alert,
  Linking,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { Colors } from '../../constants';
import { useAuthStore } from '../../stores/authStore';
import { logoutUser } from '../../services/auth';
import { notificationsApi, settingsApi, childrenApi } from '../../services/api';
import { router } from 'expo-router';
import type { NotificationPreferences, Child } from '../../types';

interface SettingItemProps {
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  value?: string;
  onPress?: () => void;
  showArrow?: boolean;
  danger?: boolean;
}

function SettingItem({ icon, label, value, onPress, showArrow = true, danger }: SettingItemProps) {
  return (
    <TouchableOpacity
      style={styles.settingItem}
      onPress={onPress}
      activeOpacity={onPress ? 0.6 : 1}
      disabled={!onPress}
    >
      <View style={[styles.settingIcon, danger && styles.settingIconDanger]}>
        <Ionicons name={icon} size={20} color={danger ? Colors.danger : Colors.primary} />
      </View>
      <Text style={[styles.settingLabel, danger && styles.settingLabelDanger]}>
        {label}
      </Text>
      <View style={styles.settingRight}>
        {value && <Text style={styles.settingValue}>{value}</Text>}
        {showArrow && onPress && (
          <Ionicons name="chevron-forward" size={18} color={Colors.textTertiary} />
        )}
      </View>
    </TouchableOpacity>
  );
}

interface ToggleItemProps {
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  value: boolean;
  onToggle: (value: boolean) => void;
}

function ToggleItem({ icon, label, value, onToggle }: ToggleItemProps) {
  return (
    <View style={styles.settingItem}>
      <View style={styles.settingIcon}>
        <Ionicons name={icon} size={20} color={Colors.primary} />
      </View>
      <Text style={styles.settingLabel}>{label}</Text>
      <Switch
        value={value}
        onValueChange={onToggle}
        trackColor={{ false: Colors.grayLight, true: Colors.primary + '60' }}
        thumbColor={value ? Colors.primary : Colors.gray}
      />
    </View>
  );
}

export default function SettingsScreen() {
  const user = useAuthStore((s) => s.user);

  const [children, setChildren] = useState<Child[]>([]);
  const [notifPrefs, setNotifPrefs] = useState<NotificationPreferences>({
    routeDeviation: true,
    dangerZone: true,
    arrival: true,
    departure: true,
    communityReports: true,
  });

  useEffect(() => {
    loadPreferences();
    loadChildren();
  }, []);

  const loadChildren = async () => {
    try {
      const data = await childrenApi.list();
      setChildren(data.children);
    } catch {
      // Use empty
    }
  };

  const loadPreferences = async () => {
    try {
      const prefs = await notificationsApi.getPreferences();
      setNotifPrefs(prefs);
    } catch {
      // Use defaults
    }
  };

  const updateNotifPref = async (key: keyof NotificationPreferences, value: boolean) => {
    const updated = { ...notifPrefs, [key]: value };
    setNotifPrefs(updated);
    try {
      await notificationsApi.updatePreferences({ [key]: value });
    } catch {
      // Revert on failure
      setNotifPrefs(notifPrefs);
    }
  };

  const handleLogout = () => {
    Alert.alert(
      'ログアウト',
      'ログアウトしますか？',
      [
        { text: 'キャンセル', style: 'cancel' },
        {
          text: 'ログアウト',
          style: 'destructive',
          onPress: async () => {
            await logoutUser();
            router.replace('/(auth)/login');
          },
        },
      ]
    );
  };

  const handleDeleteAccount = () => {
    Alert.alert(
      'アカウント削除',
      'アカウントを削除すると、すべてのデータが失われます。この操作は取り消せません。',
      [
        { text: 'キャンセル', style: 'cancel' },
        {
          text: '削除する',
          style: 'destructive',
          onPress: async () => {
            try {
              await settingsApi.deleteAccount();
              await logoutUser();
              router.replace('/(auth)/login');
            } catch {
              Alert.alert('エラー', 'アカウントの削除に失敗しました');
            }
          },
        },
      ]
    );
  };

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>設定</Text>
      </View>

      <ScrollView style={styles.scrollView} contentContainerStyle={styles.content}>
        {/* Profile */}
        <View style={styles.profileCard}>
          <View style={styles.avatar}>
            <Ionicons name="person" size={28} color={Colors.primary} />
          </View>
          <View style={styles.profileInfo}>
            <Text style={styles.profileName}>{user?.name || '保護者'}</Text>
            <Text style={styles.profileEmail}>{user?.email || ''}</Text>
          </View>
        </View>

        {/* Children */}
        <Text style={styles.sectionTitle}>お子様</Text>
        <View style={styles.section}>
          <SettingItem
            icon="person-circle-outline"
            label="お子様のプロフィール"
            value={children.length > 0 ? children.map((c) => c.name).join(', ') : undefined}
            onPress={() => {
              if (children.length > 0) {
                router.push(`/(main)/child/${children[0].id}` as any);
              }
            }}
          />
          <SettingItem
            icon="watch-outline"
            label="GPSデバイス設定"
            value={children.length > 0 && children[0].gpsDeviceType ? children[0].gpsDeviceType : undefined}
            onPress={() => {
              Alert.alert('GPSデバイス設定', 'GPSデバイスの管理はオンボーディングから再設定できます。');
            }}
          />
        </View>

        {/* Route */}
        <Text style={styles.sectionTitle}>ルート設定</Text>
        <View style={styles.section}>
          <SettingItem
            icon="home-outline"
            label="自宅の場所"
            onPress={() => {
              router.push('/(onboarding)/home-location' as any);
            }}
          />
          <SettingItem
            icon="school-outline"
            label="学校の設定"
            value={children.length > 0 ? children[0].schoolName : undefined}
            onPress={() => {
              router.push('/(onboarding)/school-select' as any);
            }}
          />
          <SettingItem
            icon="time-outline"
            label="時間帯設定"
            value="7:30 - 8:15"
            onPress={() => {
              Alert.alert('時間帯設定', '通学時間帯の設定は今後のアップデートで対応予定です。');
            }}
          />
        </View>

        {/* Notifications */}
        <Text style={styles.sectionTitle}>通知設定</Text>
        <View style={styles.section}>
          <ToggleItem
            icon="navigate-outline"
            label="ルート逸脱"
            value={notifPrefs.routeDeviation}
            onToggle={(v) => updateNotifPref('routeDeviation', v)}
          />
          <ToggleItem
            icon="warning-outline"
            label="危険エリア接近"
            value={notifPrefs.dangerZone}
            onToggle={(v) => updateNotifPref('dangerZone', v)}
          />
          <ToggleItem
            icon="school-outline"
            label="学校到着"
            value={notifPrefs.arrival}
            onToggle={(v) => updateNotifPref('arrival', v)}
          />
          <ToggleItem
            icon="exit-outline"
            label="学校出発"
            value={notifPrefs.departure}
            onToggle={(v) => updateNotifPref('departure', v)}
          />
          <ToggleItem
            icon="people-outline"
            label="地域の報告"
            value={notifPrefs.communityReports}
            onToggle={(v) => updateNotifPref('communityReports', v)}
          />
        </View>

        {/* Account */}
        <Text style={styles.sectionTitle}>アカウント</Text>
        <View style={styles.section}>
          <SettingItem
            icon="document-text-outline"
            label="利用規約"
            onPress={() => {
              Linking.openURL('https://guardian-ai.jp/terms');
            }}
          />
          <SettingItem
            icon="shield-outline"
            label="プライバシーポリシー"
            onPress={() => {
              Linking.openURL('https://guardian-ai.jp/privacy');
            }}
          />
          <SettingItem
            icon="help-circle-outline"
            label="ヘルプ・お問い合わせ"
            onPress={() => {
              Linking.openURL('mailto:support@guardian-ai.jp');
            }}
          />
          <SettingItem
            icon="log-out-outline"
            label="ログアウト"
            onPress={handleLogout}
            showArrow={false}
            danger
          />
          <SettingItem
            icon="trash-outline"
            label="アカウントを削除"
            onPress={handleDeleteAccount}
            showArrow={false}
            danger
          />
        </View>

        {/* Version */}
        <Text style={styles.version}>Guardian AI v1.0.0</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  header: {
    paddingHorizontal: 20,
    paddingVertical: 14,
    backgroundColor: Colors.white,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: Colors.border,
  },
  headerTitle: {
    fontSize: 22,
    fontWeight: '700',
    color: Colors.text,
  },
  scrollView: {
    flex: 1,
  },
  content: {
    paddingBottom: 40,
  },
  profileCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.white,
    margin: 16,
    padding: 16,
    borderRadius: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  avatar: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: Colors.primaryLight,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 14,
  },
  profileInfo: {
    flex: 1,
  },
  profileName: {
    fontSize: 18,
    fontWeight: '700',
    color: Colors.text,
    marginBottom: 2,
  },
  profileEmail: {
    fontSize: 13,
    color: Colors.textSecondary,
  },
  sectionTitle: {
    fontSize: 13,
    fontWeight: '600',
    color: Colors.textSecondary,
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 8,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  section: {
    backgroundColor: Colors.white,
    marginHorizontal: 16,
    borderRadius: 12,
    overflow: 'hidden',
  },
  settingItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 14,
    paddingHorizontal: 14,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: Colors.border,
  },
  settingIcon: {
    width: 32,
    height: 32,
    borderRadius: 8,
    backgroundColor: Colors.primaryLight,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  settingIconDanger: {
    backgroundColor: '#FFEBEE',
  },
  settingLabel: {
    flex: 1,
    fontSize: 15,
    color: Colors.text,
  },
  settingLabelDanger: {
    color: Colors.danger,
  },
  settingRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  settingValue: {
    fontSize: 13,
    color: Colors.textTertiary,
  },
  version: {
    textAlign: 'center',
    fontSize: 12,
    color: Colors.textTertiary,
    paddingTop: 24,
  },
});
