import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Colors } from '../constants';
import type { Alert } from '../types';

interface Props {
  alert: Alert;
  onPress: (alert: Alert) => void;
}

const SEVERITY_CONFIG: Record<string, { icon: keyof typeof Ionicons.glyphMap; color: string; bg: string }> = {
  info: { icon: 'information-circle', color: Colors.primary, bg: Colors.primaryLight },
  warning: { icon: 'warning', color: Colors.warning, bg: '#FFF3E0' },
  critical: { icon: 'alert-circle', color: Colors.danger, bg: '#FFEBEE' },
};

export default function AlertItem({ alert, onPress }: Props) {
  const config = SEVERITY_CONFIG[alert.severity] || SEVERITY_CONFIG.info;
  const date = new Date(alert.createdAt);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  const diffHour = Math.floor(diffMin / 60);

  let timeLabel: string;
  if (diffMin < 1) {
    timeLabel = 'たった今';
  } else if (diffMin < 60) {
    timeLabel = `${diffMin}分前`;
  } else if (diffHour < 24) {
    timeLabel = `${diffHour}時間前`;
  } else {
    timeLabel = `${date.getMonth() + 1}/${date.getDate()} ${date.getHours()}:${date.getMinutes().toString().padStart(2, '0')}`;
  }

  return (
    <TouchableOpacity
      style={[styles.container, !alert.read && styles.unread]}
      onPress={() => onPress(alert)}
      activeOpacity={0.7}
    >
      <View style={[styles.iconContainer, { backgroundColor: config.bg }]}>
        <Ionicons name={config.icon} size={22} color={config.color} />
      </View>
      <View style={styles.content}>
        <View style={styles.header}>
          <Text style={[styles.title, !alert.read && styles.titleUnread]} numberOfLines={1}>
            {alert.title}
          </Text>
          <Text style={styles.time}>{timeLabel}</Text>
        </View>
        <Text style={styles.message} numberOfLines={2}>
          {alert.message}
        </Text>
      </View>
      {!alert.read && <View style={styles.unreadDot} />}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    backgroundColor: Colors.white,
    padding: 16,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: Colors.border,
  },
  unread: {
    backgroundColor: '#F8FAFF',
  },
  iconContainer: {
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
    marginTop: 2,
  },
  content: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  title: {
    fontSize: 15,
    fontWeight: '500',
    color: Colors.text,
    flex: 1,
    marginRight: 8,
  },
  titleUnread: {
    fontWeight: '700',
  },
  time: {
    fontSize: 12,
    color: Colors.textTertiary,
  },
  message: {
    fontSize: 13,
    color: Colors.textSecondary,
    lineHeight: 18,
  },
  unreadDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: Colors.primary,
    marginTop: 8,
    marginLeft: 4,
  },
});
