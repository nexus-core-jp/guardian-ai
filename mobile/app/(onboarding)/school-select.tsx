import React, { useEffect, useState, useCallback } from 'react';
import { View, Text, StyleSheet, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router, useLocalSearchParams } from 'expo-router';
import { Colors } from '../../constants';
import OnboardingProgress from '../../components/OnboardingProgress';
import SchoolSearchInput from '../../components/SchoolSearchInput';
import { schoolsApi } from '../../services/api';
import type { School } from '../../types';

export default function SchoolSelectScreen() {
  const params = useLocalSearchParams<{
    homeLat: string;
    homeLng: string;
    homeAddress: string;
  }>();

  const homeLat = parseFloat(params.homeLat || '35.6812');
  const homeLng = parseFloat(params.homeLng || '139.7671');

  const [nearbySchools, setNearbySchools] = useState<School[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadNearbySchools();
  }, []);

  const loadNearbySchools = async () => {
    try {
      const schools = await schoolsApi.nearby(homeLat, homeLng);
      setNearbySchools(schools);
    } catch {
      // Will show empty list
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelect = useCallback(
    (school: School) => {
      router.push({
        pathname: '/(onboarding)/gps-device',
        params: {
          homeLat: params.homeLat,
          homeLng: params.homeLng,
          homeAddress: params.homeAddress,
          schoolId: school.id,
          schoolName: school.name,
          schoolLat: school.latitude.toString(),
          schoolLng: school.longitude.toString(),
        },
      });
    },
    [params]
  );

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <OnboardingProgress currentStep={1} totalSteps={4} />
      <Text style={styles.title}>通学先の学校を選択</Text>
      <Text style={styles.description}>
        お子様が通う学校を選んでください
      </Text>

      {isLoading ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={Colors.primary} />
          <Text style={styles.loadingText}>近くの学校を検索中...</Text>
        </View>
      ) : (
        <SchoolSearchInput
          currentLat={homeLat}
          currentLng={homeLng}
          onSelect={handleSelect}
          nearbySchools={nearbySchools}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.white,
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
    color: Colors.text,
    textAlign: 'center',
    marginBottom: 8,
  },
  description: {
    fontSize: 14,
    color: Colors.textSecondary,
    textAlign: 'center',
    marginBottom: 20,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    gap: 16,
  },
  loadingText: {
    fontSize: 14,
    color: Colors.textSecondary,
  },
});
