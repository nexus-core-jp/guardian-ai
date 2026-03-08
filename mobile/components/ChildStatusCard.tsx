import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Colors } from '../constants';
import type { ChildLocation } from '../types';

interface Props {
  childLocation: ChildLocation | null;
  isLoading?: boolean;
}

const STATUS_CONFIG: Record<string, { icon: keyof typeof Ionicons.glyphMap; color: string }> = {
  at_home: { icon: 'home', color: Colors.safe },
  at_school: { icon: 'school', color: Colors.safe },
  on_route: { icon: 'walk', color: Colors.primary },
  moving: { icon: 'navigate', color: Colors.warning },
  unknown: { icon: 'help-circle', color: Colors.gray },
};

export default function ChildStatusCard({ childLocation, isLoading }: Props) {
  if (isLoading) {
    return (
      <View style={styles.card}>
        <View style={styles.loadingDot} />
        <Text style={styles.loadingText}>位置情報を取得中...</Text>
      </View>
    );
  }

  if (!childLocation) {
    return (
      <View style={styles.card}>
        <Ionicons name="location-outline" size={24} color={Colors.gray} />
        <Text style={styles.noDataText}>位置情報がありません</Text>
      </View>
    );
  }

  const config = STATUS_CONFIG[childLocation.status] || STATUS_CONFIG.unknown;
  const time = new Date(childLocation.location.timestamp);
  const timeStr = `${time.getHours()}:${time.getMinutes().toString().padStart(2, '0')}`;

  return (
    <View style={styles.card}>
      <View style={[styles.iconContainer, { backgroundColor: config.color + '20' }]}>
        <Ionicons name={config.icon} size={22} color={config.color} />
      </View>
      <View style={styles.info}>
        <Text style={styles.name}>{childLocation.childName}</Text>
        <Text style={[styles.status, { color: config.color }]}>
          {childLocation.statusLabel}
        </Text>
      </View>
      <View style={styles.meta}>
        <Text style={styles.time}>{timeStr}</Text>
        {childLocation.batteryLevel != null && (
          <View style={styles.battery}>
            <Ionicons
              name={childLocation.batteryLevel > 20 ? 'battery-half' : 'battery-dead'}
              size={16}
              color={childLocation.batteryLevel > 20 ? Colors.safe : Colors.danger}
            />
            <Text style={styles.batteryText}>{childLocation.batteryLevel}%</Text>
          </View>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.white,
    borderRadius: 16,
    padding: 16,
    marginHorizontal: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 8,
    elevation: 3,
  },
  iconContainer: {
    width: 44,
    height: 44,
    borderRadius: 22,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  info: {
    flex: 1,
  },
  name: {
    fontSize: 16,
    fontWeight: '700',
    color: Colors.text,
    marginBottom: 2,
  },
  status: {
    fontSize: 14,
    fontWeight: '500',
  },
  meta: {
    alignItems: 'flex-end',
  },
  time: {
    fontSize: 12,
    color: Colors.textSecondary,
    marginBottom: 4,
  },
  battery: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
  },
  batteryText: {
    fontSize: 11,
    color: Colors.textSecondary,
  },
  loadingDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: Colors.primary,
    marginRight: 10,
    opacity: 0.6,
  },
  loadingText: {
    fontSize: 14,
    color: Colors.textSecondary,
  },
  noDataText: {
    fontSize: 14,
    color: Colors.gray,
    marginLeft: 8,
  },
});
