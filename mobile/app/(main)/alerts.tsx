import React from 'react';
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  ActivityIndicator,
  TouchableOpacity,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { Colors } from '../../constants';
import AlertItem from '../../components/AlertItem';
import { useAlerts } from '../../hooks/useAlerts';
import type { Alert } from '../../types';

export default function AlertsScreen() {
  const {
    alerts,
    isLoading,
    isRefreshing,
    error,
    hasMore,
    refresh,
    loadMore,
    markAsRead,
    markAllAsRead,
    unreadCount,
  } = useAlerts();

  const handleAlertPress = (alert: Alert) => {
    if (!alert.read) {
      markAsRead(alert.id);
    }
    // Could navigate to alert detail in future
  };

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>通知</Text>
        {unreadCount > 0 && (
          <TouchableOpacity onPress={markAllAsRead} activeOpacity={0.6}>
            <Text style={styles.markAllRead}>すべて既読</Text>
          </TouchableOpacity>
        )}
      </View>

      {/* Alert list */}
      {isLoading && alerts.length === 0 ? (
        <View style={styles.centerContainer}>
          <ActivityIndicator size="large" color={Colors.primary} />
        </View>
      ) : error && alerts.length === 0 ? (
        <View style={styles.centerContainer}>
          <Ionicons name="cloud-offline-outline" size={48} color={Colors.gray} />
          <Text style={styles.errorText}>{error}</Text>
          <TouchableOpacity style={styles.retryButton} onPress={refresh}>
            <Text style={styles.retryText}>再試行</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <FlatList
          data={alerts}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => (
            <AlertItem alert={item} onPress={handleAlertPress} />
          )}
          onRefresh={refresh}
          refreshing={isRefreshing}
          onEndReached={loadMore}
          onEndReachedThreshold={0.3}
          ListEmptyComponent={
            <View style={styles.emptyContainer}>
              <Ionicons name="shield-checkmark-outline" size={56} color={Colors.grayLight} />
              <Text style={styles.emptyTitle}>安全に通学中です</Text>
              <Text style={styles.emptyText}>
                {'ルート逸脱・危険エリア接近・不審者情報など\nお子様の安全に関する通知がここに表示されます'}
              </Text>
              <View style={styles.alertTypesCard}>
                <Text style={styles.alertTypesText}>
                  通知の種類: ルート逸脱 / 危険エリア / 到着・出発 / 地域の報告
                </Text>
              </View>
            </View>
          }
          ListFooterComponent={
            hasMore && alerts.length > 0 ? (
              <View style={styles.footer}>
                <ActivityIndicator size="small" color={Colors.primary} />
              </View>
            ) : null
          }
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
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
  markAllRead: {
    fontSize: 14,
    color: Colors.primary,
    fontWeight: '600',
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 40,
    gap: 12,
  },
  errorText: {
    fontSize: 14,
    color: Colors.textSecondary,
    textAlign: 'center',
  },
  retryButton: {
    paddingHorizontal: 20,
    paddingVertical: 10,
    backgroundColor: Colors.primaryLight,
    borderRadius: 10,
    marginTop: 8,
  },
  retryText: {
    fontSize: 14,
    fontWeight: '600',
    color: Colors.primary,
  },
  emptyContainer: {
    alignItems: 'center',
    paddingTop: 80,
    paddingHorizontal: 40,
    gap: 10,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: Colors.textSecondary,
    marginTop: 8,
  },
  emptyText: {
    fontSize: 14,
    color: Colors.textTertiary,
    textAlign: 'center',
    lineHeight: 20,
  },
  alertTypesCard: {
    backgroundColor: Colors.primaryLight,
    borderRadius: 10,
    padding: 12,
    marginTop: 16,
  },
  alertTypesText: {
    fontSize: 12,
    color: Colors.primary,
  },
  footer: {
    paddingVertical: 20,
  },
});
