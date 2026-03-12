import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { Colors, GPS_DEVICES } from '../../constants';
import OnboardingProgress from '../../components/OnboardingProgress';
import { useOnboardingStore } from '../../stores/onboardingStore';

export default function GpsDeviceScreen() {
  const onboarding = useOnboardingStore();
  const [selectedDevice, setSelectedDevice] = useState<string | null>(null);

  const handleNext = (deviceId?: string) => {
    onboarding.setGpsDevice(deviceId || selectedDevice || 'none');
    router.push('/(onboarding)/complete');
  };

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <OnboardingProgress currentStep={2} totalSteps={4} />
      <Text style={styles.title}>GPSデバイスの選択</Text>
      <Text style={styles.description}>
        お子様が使用しているGPSデバイスを{'\n'}選んでください
      </Text>
      <Text style={styles.helpNote}>
        GPSデバイスと連携すると、リアルタイムの{'\n'}位置追跡と自動アラートが利用できます
      </Text>

      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.grid}
        showsVerticalScrollIndicator={false}
      >
        {GPS_DEVICES.map((device) => (
          <TouchableOpacity
            key={device.id}
            style={[
              styles.deviceCard,
              selectedDevice === device.id && styles.deviceCardSelected,
            ]}
            onPress={() => {
              setSelectedDevice(device.id);
              // Auto-advance after short delay for better UX
              setTimeout(() => handleNext(device.id), 300);
            }}
            activeOpacity={0.7}
          >
            <Text style={styles.deviceIcon}>{device.icon}</Text>
            <Text
              style={[
                styles.deviceName,
                selectedDevice === device.id && styles.deviceNameSelected,
              ]}
            >
              {device.name}
            </Text>
            {selectedDevice === device.id && (
              <View style={styles.checkmark}>
                <Ionicons name="checkmark-circle" size={22} color={Colors.primary} />
              </View>
            )}
          </TouchableOpacity>
        ))}
      </ScrollView>

      <View style={styles.footer}>
        <TouchableOpacity onPress={() => handleNext('none')} activeOpacity={0.6}>
          <Text style={styles.skipText}>GPSなしではじめる</Text>
        </TouchableOpacity>
        <Text style={styles.skipNote}>※ あとから設定画面で追加できます</Text>
      </View>
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
    lineHeight: 22,
    marginBottom: 20,
  },
  helpNote: {
    fontSize: 13,
    color: Colors.textSecondary,
    textAlign: 'center',
    marginBottom: 12,
    paddingHorizontal: 20,
  },
  scrollView: {
    flex: 1,
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    paddingHorizontal: 16,
    gap: 12,
    justifyContent: 'center',
  },
  deviceCard: {
    width: '45%',
    backgroundColor: Colors.grayUltraLight,
    borderRadius: 16,
    padding: 20,
    alignItems: 'center',
    borderWidth: 2,
    borderColor: 'transparent',
    position: 'relative',
  },
  deviceCardSelected: {
    borderColor: Colors.primary,
    backgroundColor: Colors.primaryLight,
  },
  deviceIcon: {
    fontSize: 32,
    marginBottom: 10,
  },
  deviceName: {
    fontSize: 14,
    fontWeight: '600',
    color: Colors.text,
    textAlign: 'center',
  },
  deviceNameSelected: {
    color: Colors.primary,
  },
  checkmark: {
    position: 'absolute',
    top: 10,
    right: 10,
  },
  footer: {
    paddingVertical: 20,
    alignItems: 'center',
  },
  skipText: {
    fontSize: 15,
    color: Colors.textSecondary,
    textDecorationLine: 'underline',
  },
  skipNote: {
    fontSize: 12,
    color: Colors.textTertiary,
    marginTop: 6,
  },
});
