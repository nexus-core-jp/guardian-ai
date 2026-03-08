import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Colors, DANGER_TYPES } from '../constants';
import type { DangerZone } from '../types';

interface Props {
  dangerZone: DangerZone;
  onPress?: (zone: DangerZone) => void;
  onConfirm?: (zone: DangerZone) => void;
}

const TYPE_ICONS: Record<string, keyof typeof Ionicons.glyphMap> = {
  suspicious_person: 'person-circle-outline',
  traffic: 'car-outline',
  dark_road: 'moon-outline',
  other: 'alert-circle-outline',
};

export default function DangerReportCard({ dangerZone, onPress, onConfirm }: Props) {
  const typeConfig = DANGER_TYPES.find((t) => t.id === dangerZone.type);
  const icon = TYPE_ICONS[dangerZone.type] || 'alert-circle-outline';

  const date = new Date(dangerZone.reportedAt);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffHour = Math.floor(diffMs / 3600000);

  let timeLabel: string;
  if (diffHour < 1) {
    const diffMin = Math.floor(diffMs / 60000);
    timeLabel = diffMin < 1 ? 'たった今' : `${diffMin}分前`;
  } else if (diffHour < 24) {
    timeLabel = `${diffHour}時間前`;
  } else {
    timeLabel = `${Math.floor(diffHour / 24)}日前`;
  }

  return (
    <TouchableOpacity
      style={styles.card}
      onPress={() => onPress?.(dangerZone)}
      activeOpacity={0.7}
      disabled={!onPress}
    >
      <View style={styles.header}>
        <View style={styles.typeContainer}>
          <Ionicons name={icon} size={20} color={Colors.danger} />
          <Text style={styles.typeLabel}>{typeConfig?.label || dangerZone.typeLabel}</Text>
        </View>
        <Text style={styles.time}>{timeLabel}</Text>
      </View>

      {dangerZone.description && (
        <Text style={styles.description} numberOfLines={2}>
          {dangerZone.description}
        </Text>
      )}

      <View style={styles.footer}>
        <View style={styles.confirmInfo}>
          <Ionicons name="people-outline" size={14} color={Colors.textSecondary} />
          <Text style={styles.confirmText}>
            {dangerZone.confirmCount}人が確認
          </Text>
        </View>
        {onConfirm && !dangerZone.confirmed && (
          <TouchableOpacity
            style={styles.confirmButton}
            onPress={() => onConfirm(dangerZone)}
          >
            <Ionicons name="checkmark-circle-outline" size={16} color={Colors.primary} />
            <Text style={styles.confirmButtonText}>確認する</Text>
          </TouchableOpacity>
        )}
        {dangerZone.confirmed && (
          <View style={styles.confirmedBadge}>
            <Ionicons name="checkmark-circle" size={14} color={Colors.safe} />
            <Text style={styles.confirmedText}>確認済み</Text>
          </View>
        )}
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: Colors.white,
    borderRadius: 12,
    padding: 14,
    marginHorizontal: 16,
    marginBottom: 10,
    borderLeftWidth: 3,
    borderLeftColor: Colors.danger,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  typeContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  typeLabel: {
    fontSize: 15,
    fontWeight: '600',
    color: Colors.text,
  },
  time: {
    fontSize: 12,
    color: Colors.textTertiary,
  },
  description: {
    fontSize: 13,
    color: Colors.textSecondary,
    lineHeight: 18,
    marginBottom: 8,
  },
  footer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  confirmInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  confirmText: {
    fontSize: 12,
    color: Colors.textSecondary,
  },
  confirmButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 14,
    backgroundColor: Colors.primaryLight,
  },
  confirmButtonText: {
    fontSize: 12,
    fontWeight: '600',
    color: Colors.primary,
  },
  confirmedBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
  },
  confirmedText: {
    fontSize: 12,
    color: Colors.safe,
    fontWeight: '500',
  },
});
