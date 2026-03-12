import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { Colors } from '../../constants';
import OnboardingProgress from '../../components/OnboardingProgress';
import SafeRouteMap from '../../components/SafeRouteMap';
import RiskBadge from '../../components/RiskBadge';
import { onboardingApi } from '../../services/api';
import { useAuthStore } from '../../stores/authStore';
import { useOnboardingStore } from '../../stores/onboardingStore';
import type { SafeRoute } from '../../types';

export default function CompleteScreen() {
  const onboarding = useOnboardingStore();

  const [route, setRoute] = useState<SafeRoute | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const setOnboarded = useAuthStore((s) => s.setOnboarded);

  const homeLat = onboarding.homeLat;
  const homeLng = onboarding.homeLng;
  const schoolLat = onboarding.schoolLat;
  const schoolLng = onboarding.schoolLng;

  useEffect(() => {
    calculateRoute();
  }, []);

  const calculateRoute = async () => {
    try {
      // ルート計算はオンボーディング完了後にサーバー側で行うため、
      // ここでは地図表示のみ
    } catch {
      // ignore
    } finally {
      setIsLoading(false);
    }
  };

  const handleStart = async () => {
    setIsSaving(true);
    try {
      await onboardingApi.complete({
        homeLatitude: homeLat,
        homeLongitude: homeLng,
        homeAddress: onboarding.homeAddress,
        schoolId: onboarding.schoolId,
        schoolName: onboarding.schoolName,
        gpsDeviceType: onboarding.gpsDevice !== 'none' ? onboarding.gpsDevice : undefined,
        childName: onboarding.childName || 'お子さま',
        childGrade: onboarding.childGrade,
      });
      setOnboarded(true);
      onboarding.reset();
      router.replace('/(main)/map');
    } catch (error) {
      Alert.alert(
        'エラー',
        error instanceof Error ? error.message : '設定の保存に失敗しました。',
        [
          { text: '再試行', onPress: () => handleStart() },
          { text: 'キャンセル', style: 'cancel' },
        ]
      );
    } finally {
      setIsSaving(false);
    }
  };

  const truncatedAddress = onboarding.homeAddress
    ? onboarding.homeAddress.length > 20
      ? onboarding.homeAddress.slice(0, 20) + '...'
      : onboarding.homeAddress
    : '';

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <OnboardingProgress currentStep={3} totalSteps={4} />

      <View style={styles.header}>
        <View style={styles.successIcon}>
          <Ionicons name="checkmark-circle" size={48} color={Colors.safe} />
        </View>
        <Text style={styles.title}>設定完了!</Text>
        <Text style={styles.schoolName}>
          {onboarding.schoolName || '学校'}への通学ルート
        </Text>
      </View>

      {/* Setup summary card */}
      <View style={styles.summaryCard}>
        <View style={styles.summaryRow}>
          <Ionicons name="person" size={16} color={Colors.primary} />
          <Text style={styles.summaryLabel}>
            {onboarding.childName || 'お子さま'}
            {onboarding.childGrade ? ` (${onboarding.childGrade}年生)` : ''}
          </Text>
        </View>
        <View style={styles.summaryRow}>
          <Ionicons name="school" size={16} color={Colors.primary} />
          <Text style={styles.summaryLabel}>{onboarding.schoolName || '未設定'}</Text>
        </View>
        {truncatedAddress ? (
          <View style={styles.summaryRow}>
            <Ionicons name="home" size={16} color={Colors.primary} />
            <Text style={styles.summaryLabel}>{truncatedAddress}</Text>
          </View>
        ) : null}
      </View>

      {/* Route map */}
      <View style={styles.mapContainer}>
        {isLoading ? (
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="large" color={Colors.primary} />
            <Text style={styles.loadingText}>最適なルートを計算中...</Text>
          </View>
        ) : (
          <>
            <SafeRouteMap
              safeRoute={route}
              initialRegion={{
                latitude: (homeLat + schoolLat) / 2,
                longitude: (homeLng + schoolLng) / 2,
                latitudeDelta: Math.abs(homeLat - schoolLat) * 1.8 + 0.005,
                longitudeDelta: Math.abs(homeLng - schoolLng) * 1.8 + 0.005,
              }}
              style={styles.map}
            />
            {route && (
              <View style={styles.routeInfo}>
                <View style={styles.routeInfoRow}>
                  <Ionicons name="walk" size={18} color={Colors.textSecondary} />
                  <Text style={styles.routeInfoText}>
                    徒歩 約{route.estimatedWalkMinutes}分
                  </Text>
                </View>
                <RiskBadge level={route.overallRiskLevel} size="small" />
              </View>
            )}
          </>
        )}
      </View>

      <Text style={styles.message}>
        AIが通学路の安全度を毎日分析してお知らせします
      </Text>

      <View style={styles.buttonContainer}>
        <TouchableOpacity
          style={[styles.startButton, isSaving && styles.buttonDisabled]}
          onPress={handleStart}
          disabled={isSaving}
          activeOpacity={0.8}
        >
          {isSaving ? (
            <ActivityIndicator color={Colors.white} />
          ) : (
            <Text style={styles.startButtonText}>はじめる</Text>
          )}
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.white,
  },
  header: {
    alignItems: 'center',
    marginBottom: 12,
  },
  successIcon: {
    marginBottom: 8,
  },
  title: {
    fontSize: 28,
    fontWeight: '800',
    color: Colors.text,
    marginBottom: 6,
  },
  schoolName: {
    fontSize: 15,
    color: Colors.textSecondary,
  },
  summaryCard: {
    marginHorizontal: 20,
    marginBottom: 12,
    backgroundColor: Colors.grayUltraLight,
    borderRadius: 12,
    padding: 14,
    gap: 8,
  },
  summaryRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  summaryLabel: {
    fontSize: 13,
    color: Colors.text,
    fontWeight: '500',
  },
  mapContainer: {
    flex: 1,
    marginHorizontal: 16,
    borderRadius: 16,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: Colors.border,
    position: 'relative',
  },
  map: {
    flex: 1,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    gap: 12,
  },
  loadingText: {
    fontSize: 14,
    color: Colors.textSecondary,
  },
  routeInfo: {
    position: 'absolute',
    bottom: 12,
    left: 12,
    right: 12,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: Colors.white + 'F0',
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  routeInfoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  routeInfoText: {
    fontSize: 14,
    fontWeight: '600',
    color: Colors.text,
  },
  message: {
    fontSize: 15,
    color: Colors.textSecondary,
    textAlign: 'center',
    paddingVertical: 16,
  },
  buttonContainer: {
    paddingHorizontal: 24,
    paddingBottom: 20,
  },
  startButton: {
    backgroundColor: Colors.primary,
    borderRadius: 14,
    paddingVertical: 18,
    alignItems: 'center',
  },
  startButtonText: {
    fontSize: 17,
    fontWeight: '700',
    color: Colors.white,
  },
  buttonDisabled: {
    opacity: 0.6,
  },
});
