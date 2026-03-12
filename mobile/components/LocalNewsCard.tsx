import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Colors } from '../constants';

export interface LocalNews {
  id: string;
  type: 'suspicious_person' | 'traffic_accident' | 'construction' | 'weather' | 'event';
  title: string;
  summary: string;
  source: string;
  publishedAt: string;
  location?: string;
}

const TYPE_CONFIG: Record<string, { icon: keyof typeof Ionicons.glyphMap; color: string; label: string }> = {
  suspicious_person: { icon: 'alert-circle', color: Colors.danger, label: '不審者情報' },
  traffic_accident: { icon: 'car', color: Colors.warning, label: '交通事故' },
  construction: { icon: 'construct', color: Colors.warning, label: '工事情報' },
  weather: { icon: 'thunderstorm', color: Colors.primary, label: '気象警報' },
  event: { icon: 'information-circle', color: Colors.safe, label: '地域イベント' },
};

function getRelativeTime(dateStr: string): string {
  const now = new Date();
  const date = new Date(dateStr);
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 60) return `${diffMin}分前`;
  const diffHour = Math.floor(diffMin / 60);
  if (diffHour < 24) return `${diffHour}時間前`;
  const diffDay = Math.floor(diffHour / 24);
  return `${diffDay}日前`;
}

interface Props {
  news: LocalNews;
  onPress?: (news: LocalNews) => void;
}

export default function LocalNewsCard({ news, onPress }: Props) {
  const config = TYPE_CONFIG[news.type] || TYPE_CONFIG.event;

  return (
    <TouchableOpacity
      style={styles.card}
      onPress={() => onPress?.(news)}
      activeOpacity={0.7}
    >
      <View style={[styles.iconContainer, { backgroundColor: config.color + '15' }]}>
        <Ionicons name={config.icon} size={20} color={config.color} />
      </View>
      <View style={styles.content}>
        <View style={styles.topRow}>
          <View style={[styles.typeBadge, { backgroundColor: config.color + '15' }]}>
            <Text style={[styles.typeText, { color: config.color }]}>{config.label}</Text>
          </View>
          <Text style={styles.time}>{getRelativeTime(news.publishedAt)}</Text>
        </View>
        <Text style={styles.title} numberOfLines={2}>{news.title}</Text>
        <Text style={styles.summary} numberOfLines={2}>{news.summary}</Text>
        <View style={styles.sourceRow}>
          <Ionicons name="link-outline" size={12} color={Colors.textTertiary} />
          <Text style={styles.source}>{news.source}</Text>
          {news.location && (
            <>
              <Ionicons name="location-outline" size={12} color={Colors.textTertiary} />
              <Text style={styles.source}>{news.location}</Text>
            </>
          )}
        </View>
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {
    flexDirection: 'row',
    backgroundColor: Colors.white,
    marginHorizontal: 16,
    marginBottom: 8,
    borderRadius: 12,
    padding: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 3,
    elevation: 1,
  },
  iconContainer: {
    width: 36,
    height: 36,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 10,
    marginTop: 2,
  },
  content: {
    flex: 1,
  },
  topRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  typeBadge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 6,
  },
  typeText: {
    fontSize: 11,
    fontWeight: '700',
  },
  time: {
    fontSize: 11,
    color: Colors.textTertiary,
  },
  title: {
    fontSize: 14,
    fontWeight: '600',
    color: Colors.text,
    marginBottom: 3,
    lineHeight: 20,
  },
  summary: {
    fontSize: 12,
    color: Colors.textSecondary,
    lineHeight: 17,
    marginBottom: 6,
  },
  sourceRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  source: {
    fontSize: 11,
    color: Colors.textTertiary,
  },
});
