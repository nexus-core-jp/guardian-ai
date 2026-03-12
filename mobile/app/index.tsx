import React from 'react';
import { View, ActivityIndicator, StyleSheet, Text } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Colors } from '../constants';

const features = [
  { icon: 'shield-checkmark' as const, label: '国土交通省データで安全ルート分析' },
  { icon: 'notifications' as const, label: '危険エリア自動アラート' },
  { icon: 'people' as const, label: '地域の保護者と見守りネットワーク' },
];

export default function SplashScreen() {
  return (
    <View style={styles.container}>
      <View style={styles.logoContainer}>
        <Text style={styles.logoText}>Guardian AI</Text>
        <Text style={styles.tagline}>AIが、通学路の安全を見守る</Text>

        <View style={styles.featuresContainer}>
          {features.map((feature, index) => (
            <View key={index} style={styles.featureRow}>
              <Ionicons name={feature.icon} size={18} color={Colors.primary} />
              <Text style={styles.featureLabel}>{feature.label}</Text>
            </View>
          ))}
        </View>
      </View>
      <ActivityIndicator size="large" color={Colors.primary} style={styles.loader} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: Colors.white,
  },
  logoContainer: {
    alignItems: 'center',
  },
  logoText: {
    fontSize: 36,
    fontWeight: '800',
    color: Colors.primary,
    letterSpacing: 1,
  },
  tagline: {
    fontSize: 15,
    color: Colors.textSecondary,
    marginTop: 8,
  },
  featuresContainer: {
    marginTop: 32,
    gap: 14,
  },
  featureRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  featureLabel: {
    fontSize: 13,
    color: Colors.textSecondary,
  },
  loader: {
    position: 'absolute',
    bottom: 100,
  },
});
