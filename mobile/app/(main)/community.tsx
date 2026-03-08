import React, { useEffect, useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  FlatList,
  Modal,
  TextInput,
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import MapView, { Circle, PROVIDER_DEFAULT } from 'react-native-maps';
import { Colors, DANGER_TYPES } from '../../constants';
import DangerReportCard from '../../components/DangerReportCard';
import { communityApi } from '../../services/api';
import { getCurrentLocation } from '../../services/location';
import type { DangerZone, DangerReport } from '../../types';

export default function CommunityScreen() {
  const [dangerZones, setDangerZones] = useState<DangerZone[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showReportModal, setShowReportModal] = useState(false);
  const [reportType, setReportType] = useState<DangerReport['type'] | null>(null);
  const [reportNote, setReportNote] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [currentLat, setCurrentLat] = useState(35.6812);
  const [currentLng, setCurrentLng] = useState(139.7671);
  const [viewMode, setViewMode] = useState<'map' | 'list'>('list');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setIsLoading(true);
    const loc = await getCurrentLocation();
    if (loc) {
      setCurrentLat(loc.latitude);
      setCurrentLng(loc.longitude);
    }

    try {
      const zones = await communityApi.getDangerZones(
        loc?.latitude || currentLat,
        loc?.longitude || currentLng
      );
      setDangerZones(zones);
    } catch {
      // Show empty
    } finally {
      setIsLoading(false);
    }
  };

  const handleConfirm = useCallback(async (zone: DangerZone) => {
    try {
      await communityApi.confirmDanger(zone.id);
      setDangerZones((prev) =>
        prev.map((z) =>
          z.id === zone.id
            ? { ...z, confirmed: true, confirmCount: z.confirmCount + 1 }
            : z
        )
      );
    } catch {
      Alert.alert('エラー', '確認に失敗しました');
    }
  }, []);

  const handleSubmitReport = async () => {
    if (!reportType) return;

    setIsSubmitting(true);
    try {
      const loc = await getCurrentLocation();
      const report: DangerReport = {
        type: reportType,
        description: reportNote || undefined,
        latitude: loc?.latitude || currentLat,
        longitude: loc?.longitude || currentLng,
      };

      const newZone = await communityApi.reportDanger(report);
      setDangerZones((prev) => [newZone, ...prev]);
      setShowReportModal(false);
      setReportType(null);
      setReportNote('');
      Alert.alert('報告完了', '危険情報を共有しました。ありがとうございます。');
    } catch {
      Alert.alert('エラー', '報告に失敗しました。もう一度お試しください。');
    } finally {
      setIsSubmitting(false);
    }
  };

  const getDensityRadius = (confirmCount: number): number => {
    // More confirmations = larger circle
    return Math.min(150, 50 + confirmCount * 20);
  };

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>地域の安全情報</Text>
        <View style={styles.viewToggle}>
          <TouchableOpacity
            style={[styles.toggleButton, viewMode === 'list' && styles.toggleActive]}
            onPress={() => setViewMode('list')}
          >
            <Ionicons
              name="list"
              size={18}
              color={viewMode === 'list' ? Colors.primary : Colors.gray}
            />
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.toggleButton, viewMode === 'map' && styles.toggleActive]}
            onPress={() => setViewMode('map')}
          >
            <Ionicons
              name="map"
              size={18}
              color={viewMode === 'map' ? Colors.primary : Colors.gray}
            />
          </TouchableOpacity>
        </View>
      </View>

      {isLoading ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={Colors.primary} />
        </View>
      ) : viewMode === 'map' ? (
        /* Heatmap view */
        <View style={styles.mapContainer}>
          <MapView
            style={styles.map}
            provider={PROVIDER_DEFAULT}
            initialRegion={{
              latitude: currentLat,
              longitude: currentLng,
              latitudeDelta: 0.02,
              longitudeDelta: 0.02,
            }}
          >
            {dangerZones.map((zone) => (
              <Circle
                key={`density-${zone.id}`}
                center={{ latitude: zone.latitude, longitude: zone.longitude }}
                radius={getDensityRadius(zone.confirmCount)}
                strokeColor="transparent"
                fillColor={Colors.danger + '30'}
                strokeWidth={0}
              />
            ))}
            {dangerZones.map((zone) => (
              <Circle
                key={zone.id}
                center={{ latitude: zone.latitude, longitude: zone.longitude }}
                radius={zone.radius}
                strokeColor={Colors.danger + '80'}
                fillColor={Colors.danger + '20'}
                strokeWidth={1}
              />
            ))}
          </MapView>
        </View>
      ) : (
        /* List view */
        <FlatList
          data={dangerZones}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => (
            <DangerReportCard
              dangerZone={item}
              onConfirm={handleConfirm}
            />
          )}
          contentContainerStyle={styles.listContent}
          onRefresh={loadData}
          refreshing={isLoading}
          ListEmptyComponent={
            <View style={styles.emptyContainer}>
              <Ionicons name="shield-checkmark-outline" size={56} color={Colors.grayLight} />
              <Text style={styles.emptyTitle}>報告はありません</Text>
              <Text style={styles.emptyText}>
                この地域では現在、危険情報の報告はありません
              </Text>
            </View>
          }
        />
      )}

      {/* Report FAB */}
      <TouchableOpacity
        style={styles.fab}
        onPress={() => setShowReportModal(true)}
        activeOpacity={0.8}
      >
        <Ionicons name="warning" size={22} color={Colors.white} />
        <Text style={styles.fabText}>危険を報告する</Text>
      </TouchableOpacity>

      {/* Report Modal */}
      <Modal
        visible={showReportModal}
        animationType="slide"
        presentationStyle="pageSheet"
        onRequestClose={() => setShowReportModal(false)}
      >
        <SafeAreaView style={styles.modalContainer}>
          <KeyboardAvoidingView
            style={styles.modalContent}
            behavior={Platform.OS === 'ios' ? 'padding' : undefined}
          >
            {/* Modal header */}
            <View style={styles.modalHeader}>
              <TouchableOpacity onPress={() => setShowReportModal(false)}>
                <Text style={styles.modalCancel}>キャンセル</Text>
              </TouchableOpacity>
              <Text style={styles.modalTitle}>危険を報告</Text>
              <View style={{ width: 70 }} />
            </View>

            {/* Report type selection */}
            <Text style={styles.sectionLabel}>種類を選択</Text>
            <View style={styles.typeGrid}>
              {DANGER_TYPES.map((type) => (
                <TouchableOpacity
                  key={type.id}
                  style={[
                    styles.typeCard,
                    reportType === type.id && styles.typeCardSelected,
                  ]}
                  onPress={() => setReportType(type.id as DangerReport['type'])}
                  activeOpacity={0.7}
                >
                  <Text style={styles.typeIcon}>{type.icon}</Text>
                  <Text
                    style={[
                      styles.typeLabel,
                      reportType === type.id && styles.typeLabelSelected,
                    ]}
                  >
                    {type.label}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            {/* Note */}
            <Text style={styles.sectionLabel}>メモ（任意）</Text>
            <TextInput
              style={styles.noteInput}
              placeholder="詳細を入力してください..."
              placeholderTextColor={Colors.textTertiary}
              value={reportNote}
              onChangeText={setReportNote}
              multiline
              numberOfLines={3}
              textAlignVertical="top"
            />

            <Text style={styles.locationNote}>
              現在地が自動的に記録されます
            </Text>

            {/* Submit */}
            <TouchableOpacity
              style={[
                styles.submitButton,
                (!reportType || isSubmitting) && styles.submitButtonDisabled,
              ]}
              onPress={handleSubmitReport}
              disabled={!reportType || isSubmitting}
              activeOpacity={0.8}
            >
              {isSubmitting ? (
                <ActivityIndicator color={Colors.white} />
              ) : (
                <Text style={styles.submitButtonText}>報告する</Text>
              )}
            </TouchableOpacity>
          </KeyboardAvoidingView>
        </SafeAreaView>
      </Modal>
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
  viewToggle: {
    flexDirection: 'row',
    backgroundColor: Colors.grayUltraLight,
    borderRadius: 8,
    padding: 2,
  },
  toggleButton: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
  },
  toggleActive: {
    backgroundColor: Colors.white,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 1,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  mapContainer: {
    flex: 1,
  },
  map: {
    flex: 1,
  },
  listContent: {
    paddingTop: 12,
    paddingBottom: 80,
  },
  emptyContainer: {
    alignItems: 'center',
    paddingTop: 80,
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
    paddingHorizontal: 40,
  },
  fab: {
    position: 'absolute',
    bottom: 24,
    right: 20,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.danger,
    borderRadius: 28,
    paddingHorizontal: 20,
    paddingVertical: 14,
    gap: 8,
    shadowColor: Colors.danger,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 6,
  },
  fabText: {
    fontSize: 15,
    fontWeight: '700',
    color: Colors.white,
  },
  // Modal
  modalContainer: {
    flex: 1,
    backgroundColor: Colors.white,
  },
  modalContent: {
    flex: 1,
    paddingHorizontal: 20,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 16,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: Colors.border,
    marginBottom: 20,
  },
  modalCancel: {
    fontSize: 15,
    color: Colors.primary,
  },
  modalTitle: {
    fontSize: 17,
    fontWeight: '700',
    color: Colors.text,
  },
  sectionLabel: {
    fontSize: 15,
    fontWeight: '600',
    color: Colors.text,
    marginBottom: 12,
    marginTop: 8,
  },
  typeGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
    marginBottom: 20,
  },
  typeCard: {
    width: '47%',
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.grayUltraLight,
    borderRadius: 12,
    padding: 14,
    gap: 10,
    borderWidth: 2,
    borderColor: 'transparent',
  },
  typeCardSelected: {
    borderColor: Colors.danger,
    backgroundColor: '#FFEBEE',
  },
  typeIcon: {
    fontSize: 22,
  },
  typeLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: Colors.text,
  },
  typeLabelSelected: {
    color: Colors.danger,
  },
  noteInput: {
    backgroundColor: Colors.grayUltraLight,
    borderRadius: 12,
    padding: 14,
    fontSize: 15,
    color: Colors.text,
    minHeight: 80,
    marginBottom: 12,
  },
  locationNote: {
    fontSize: 12,
    color: Colors.textTertiary,
    textAlign: 'center',
    marginBottom: 24,
  },
  submitButton: {
    backgroundColor: Colors.danger,
    borderRadius: 14,
    paddingVertical: 16,
    alignItems: 'center',
  },
  submitButtonDisabled: {
    opacity: 0.5,
  },
  submitButtonText: {
    fontSize: 17,
    fontWeight: '700',
    color: Colors.white,
  },
});
