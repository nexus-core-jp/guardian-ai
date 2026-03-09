import React, { useEffect, useState } from 'react';
import { View, StyleSheet, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { Colors } from '../../constants';
import SafeRouteMap from '../../components/SafeRouteMap';
import ChildStatusCard from '../../components/ChildStatusCard';
import { useChildLocation } from '../../hooks/useChildLocation';
import { useSafeRoute } from '../../hooks/useSafeRoute';
import { communityApi } from '../../services/api';
import { getCurrentLocation } from '../../services/location';
import type { DangerZone } from '../../types';
import { useChildStore } from '../../stores/childStore';

export default function MapScreen() {
  const { activeChildId, initialize: initChildren } = useChildStore();

  useEffect(() => {
    initChildren();
  }, []);

  const childId = activeChildId;
  const { location: childLocation, isLoading: isLocationLoading } = useChildLocation(childId);
  const { route } = useSafeRoute(childId);
  const [dangerZones, setDangerZones] = useState<DangerZone[]>([]);
  const [mapRegion, setMapRegion] = useState({
    latitude: 35.6812,
    longitude: 139.7671,
    latitudeDelta: 0.015,
    longitudeDelta: 0.015,
  });

  useEffect(() => {
    initializeMap();
  }, []);

  const initializeMap = async () => {
    const currentLoc = await getCurrentLocation();
    if (currentLoc) {
      setMapRegion({
        latitude: currentLoc.latitude,
        longitude: currentLoc.longitude,
        latitudeDelta: 0.015,
        longitudeDelta: 0.015,
      });

      try {
        const zones = await communityApi.getDangerZones(
          currentLoc.latitude,
          currentLoc.longitude
        );
        setDangerZones(zones.danger_zones);
      } catch {
        // Silently fail
      }
    }
  };

  const handleCenterOnChild = () => {
    if (childLocation) {
      setMapRegion({
        latitude: childLocation.location.latitude,
        longitude: childLocation.location.longitude,
        latitudeDelta: 0.008,
        longitudeDelta: 0.008,
      });
    }
  };

  return (
    <View style={styles.container}>
      {/* Full screen map */}
      <SafeRouteMap
        safeRoute={route}
        childLocation={childLocation}
        dangerZones={dangerZones}
        initialRegion={mapRegion}
        showDangerZones
        style={styles.map}
      />

      {/* Top safe area overlay */}
      <SafeAreaView style={styles.topOverlay} edges={['top']}>
        <View style={styles.topBar}>
          <View style={styles.appTitle}>
            <Ionicons name="shield-checkmark" size={20} color={Colors.primary} />
          </View>
        </View>
      </SafeAreaView>

      {/* Center on child button */}
      {childLocation && (
        <TouchableOpacity
          style={styles.centerButton}
          onPress={handleCenterOnChild}
          activeOpacity={0.8}
        >
          <Ionicons name="locate" size={22} color={Colors.primary} />
        </TouchableOpacity>
      )}

      {/* Bottom child status card */}
      <SafeAreaView style={styles.bottomOverlay} edges={['bottom']}>
        <ChildStatusCard
          childLocation={childLocation}
          isLoading={isLocationLoading}
        />
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  map: {
    ...StyleSheet.absoluteFillObject,
  },
  topOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
  },
  topBar: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  appTitle: {
    backgroundColor: Colors.white + 'E0',
    borderRadius: 20,
    padding: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 2,
  },
  centerButton: {
    position: 'absolute',
    right: 16,
    bottom: 140,
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: Colors.white,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.15,
    shadowRadius: 6,
    elevation: 4,
  },
  bottomOverlay: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    paddingBottom: 8,
  },
});
