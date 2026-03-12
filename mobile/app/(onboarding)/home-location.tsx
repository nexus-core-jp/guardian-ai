import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  TextInput,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import MapPlaceholder from '../../components/MapPlaceholder';

let MapView: any = null;
let Marker: any = null;
let PROVIDER_DEFAULT: any = null;

if (Platform.OS !== 'web') {
  const Maps = require('react-native-maps');
  MapView = Maps.default;
  Marker = Maps.Marker;
  PROVIDER_DEFAULT = Maps.PROVIDER_DEFAULT;
}
import { router } from 'expo-router';
import { Colors } from '../../constants';
import OnboardingProgress from '../../components/OnboardingProgress';
import { getCurrentLocation, reverseGeocode } from '../../services/location';
import { useOnboardingStore } from '../../stores/onboardingStore';
import type { HomeLocation } from '../../types';

const GRADES = [1, 2, 3, 4, 5, 6];

export default function HomeLocationScreen() {
  const onboarding = useOnboardingStore();
  const [location, setLocation] = useState<HomeLocation | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [editAddress, setEditAddress] = useState('');
  const [childName, setChildName] = useState(onboarding.childName);
  const [childGrade, setChildGrade] = useState<number | undefined>(onboarding.childGrade);

  useEffect(() => {
    loadCurrentLocation();
  }, []);

  const loadCurrentLocation = async () => {
    setIsLoading(true);
    const loc = await getCurrentLocation();
    if (loc) {
      const address = await reverseGeocode(loc.latitude, loc.longitude);
      setLocation({
        latitude: loc.latitude,
        longitude: loc.longitude,
        address,
      });
      setEditAddress(address);
    } else {
      // Default to Tokyo if location unavailable
      setLocation({
        latitude: 35.6812,
        longitude: 139.7671,
        address: '東京都千代田区',
      });
      setEditAddress('東京都千代田区');
    }
    setIsLoading(false);
  };

  const handleMapPress = async (event: { nativeEvent: { coordinate: { latitude: number; longitude: number } } }) => {
    const { latitude, longitude } = event.nativeEvent.coordinate;
    const address = await reverseGeocode(latitude, longitude);
    setLocation({ latitude, longitude, address });
    setEditAddress(address);
  };

  const handleConfirm = () => {
    if (!location || !childName.trim()) return;
    const finalLocation = {
      ...location,
      address: isEditing ? editAddress : location.address,
    };
    // Store in onboarding store
    onboarding.setHomeLocation(
      finalLocation.latitude,
      finalLocation.longitude,
      finalLocation.address
    );
    onboarding.setChild(childName.trim(), childGrade);
    router.push('/(onboarding)/school-select');
  };

  if (isLoading) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={Colors.primary} />
          <Text style={styles.loadingText}>現在地を取得しています...</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <OnboardingProgress currentStep={0} totalSteps={4} />
        <Text style={styles.title}>お子さまと自宅の設定</Text>
        <Text style={styles.description}>
          安全な通学ルートの計算に必要です
        </Text>

        {/* Child info section */}
        <View style={styles.childInfoSection}>
          <View style={styles.inputRow}>
            <Text style={styles.inputLabel}>お子さんのお名前</Text>
            <TextInput
              style={styles.nameInput}
              value={childName}
              onChangeText={setChildName}
              placeholder="例: たろう"
              placeholderTextColor={Colors.textTertiary}
            />
          </View>
          <View style={styles.inputRow}>
            <Text style={styles.inputLabel}>学年</Text>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.gradeScroll}>
              <View style={styles.gradeRow}>
                {GRADES.map((g) => (
                  <TouchableOpacity
                    key={g}
                    style={[styles.gradeChip, childGrade === g && styles.gradeChipSelected]}
                    onPress={() => setChildGrade(g)}
                  >
                    <Text style={[styles.gradeText, childGrade === g && styles.gradeTextSelected]}>
                      {g}年
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>
            </ScrollView>
          </View>
        </View>

        {/* Map */}
        <View style={styles.mapContainer}>
          {Platform.OS === 'web' || !MapView ? (
            <MapPlaceholder message="地図はモバイルアプリで操作できます" />
          ) : (
            location && (
              <MapView
                style={styles.map}
                provider={PROVIDER_DEFAULT}
                initialRegion={{
                  latitude: location.latitude,
                  longitude: location.longitude,
                  latitudeDelta: 0.005,
                  longitudeDelta: 0.005,
                }}
                onPress={handleMapPress}
                showsUserLocation
              >
                <Marker
                  coordinate={{
                    latitude: location.latitude,
                    longitude: location.longitude,
                  }}
                  draggable
                  onDragEnd={(e: any) => handleMapPress(e)}
                >
                  <View style={styles.markerContainer}>
                    <Ionicons name="home" size={22} color={Colors.white} />
                  </View>
                </Marker>
              </MapView>
            )
          )}
        </View>
        <Text style={styles.mapHint}>地図をタップして自宅の位置を調整できます</Text>

        {/* Address */}
        <View style={styles.addressSection}>
          {isEditing ? (
            <View style={styles.editContainer}>
              <TextInput
                style={styles.addressInput}
                value={editAddress}
                onChangeText={setEditAddress}
                placeholder="住所を入力"
                placeholderTextColor={Colors.textTertiary}
                autoFocus
              />
              <TouchableOpacity onPress={() => setIsEditing(false)}>
                <Text style={styles.doneText}>完了</Text>
              </TouchableOpacity>
            </View>
          ) : (
            <View style={styles.addressDisplay}>
              <Ionicons name="location" size={18} color={Colors.primary} />
              <Text style={styles.addressText}>{location?.address}</Text>
            </View>
          )}

          {!isEditing && (
            <TouchableOpacity onPress={() => setIsEditing(true)}>
              <Text style={styles.editLink}>住所を修正する</Text>
            </TouchableOpacity>
          )}
        </View>

        {/* Confirm button */}
        <View style={styles.buttonContainer}>
          <TouchableOpacity
            style={[styles.confirmButton, !childName.trim() && styles.buttonDisabled]}
            onPress={handleConfirm}
            activeOpacity={0.8}
            disabled={!childName.trim()}
          >
            <Text style={styles.confirmButtonText}>次へ</Text>
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.white,
  },
  flex: {
    flex: 1,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    gap: 16,
  },
  loadingText: {
    fontSize: 15,
    color: Colors.textSecondary,
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
    marginBottom: 12,
  },
  childInfoSection: {
    paddingHorizontal: 20,
    marginBottom: 12,
    gap: 10,
  },
  inputRow: {
    gap: 4,
  },
  inputLabel: {
    fontSize: 13,
    fontWeight: '600',
    color: Colors.textSecondary,
  },
  nameInput: {
    fontSize: 15,
    color: Colors.text,
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 10,
    backgroundColor: Colors.grayUltraLight,
  },
  gradeScroll: {
    flexGrow: 0,
  },
  gradeRow: {
    flexDirection: 'row',
    gap: 8,
    paddingVertical: 4,
  },
  gradeChip: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: Colors.grayUltraLight,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  gradeChipSelected: {
    backgroundColor: Colors.primaryLight,
    borderColor: Colors.primary,
  },
  gradeText: {
    fontSize: 14,
    fontWeight: '600',
    color: Colors.textSecondary,
  },
  gradeTextSelected: {
    color: Colors.primary,
  },
  mapContainer: {
    flex: 1,
    marginHorizontal: 16,
    borderRadius: 16,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: Colors.border,
  },
  map: {
    flex: 1,
  },
  mapHint: {
    fontSize: 12,
    textAlign: 'center',
    color: Colors.textTertiary,
    paddingTop: 4,
  },
  markerContainer: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: Colors.primary,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
    elevation: 4,
  },
  addressSection: {
    paddingHorizontal: 20,
    paddingTop: 12,
    alignItems: 'center',
  },
  addressDisplay: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginBottom: 6,
  },
  addressText: {
    fontSize: 15,
    color: Colors.text,
    fontWeight: '500',
  },
  editLink: {
    fontSize: 13,
    color: Colors.primary,
    textDecorationLine: 'underline',
  },
  editContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    width: '100%',
    marginBottom: 6,
  },
  addressInput: {
    flex: 1,
    fontSize: 15,
    color: Colors.text,
    borderBottomWidth: 1,
    borderBottomColor: Colors.primary,
    paddingVertical: 6,
  },
  doneText: {
    fontSize: 14,
    fontWeight: '600',
    color: Colors.primary,
  },
  buttonContainer: {
    paddingHorizontal: 24,
    paddingVertical: 16,
  },
  confirmButton: {
    backgroundColor: Colors.primary,
    borderRadius: 14,
    paddingVertical: 18,
    alignItems: 'center',
  },
  confirmButtonText: {
    fontSize: 17,
    fontWeight: '700',
    color: Colors.white,
  },
  buttonDisabled: {
    opacity: 0.5,
  },
});
