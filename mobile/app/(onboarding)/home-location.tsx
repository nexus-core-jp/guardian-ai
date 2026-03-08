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
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import MapView, { Marker, PROVIDER_DEFAULT } from 'react-native-maps';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { Colors } from '../../constants';
import OnboardingProgress from '../../components/OnboardingProgress';
import { getCurrentLocation, reverseGeocode } from '../../services/location';
import type { HomeLocation } from '../../types';

export default function HomeLocationScreen() {
  const [location, setLocation] = useState<HomeLocation | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [editAddress, setEditAddress] = useState('');

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
    if (!location) return;
    const finalLocation = {
      ...location,
      address: isEditing ? editAddress : location.address,
    };
    // Store in params for next screens
    router.push({
      pathname: '/(onboarding)/school-select',
      params: {
        homeLat: finalLocation.latitude.toString(),
        homeLng: finalLocation.longitude.toString(),
        homeAddress: finalLocation.address,
      },
    });
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
        <Text style={styles.title}>自宅の場所を確認</Text>
        <Text style={styles.description}>
          お子様の通学ルートを計算するために{'\n'}ご自宅の場所を設定してください
        </Text>

        {/* Map */}
        <View style={styles.mapContainer}>
          {location && (
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
                onDragEnd={(e) => handleMapPress(e)}
              >
                <View style={styles.markerContainer}>
                  <Ionicons name="home" size={22} color={Colors.white} />
                </View>
              </Marker>
            </MapView>
          )}
        </View>

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
            style={styles.confirmButton}
            onPress={handleConfirm}
            activeOpacity={0.8}
          >
            <Text style={styles.confirmButtonText}>ここが自宅です</Text>
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
    marginBottom: 16,
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
    paddingTop: 16,
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
    paddingVertical: 20,
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
});
