import React, { useMemo } from 'react';
import { View, StyleSheet } from 'react-native';
import MapView, { Marker, Polyline, Circle, PROVIDER_DEFAULT } from 'react-native-maps';
import { Colors } from '../constants';
import type { SafeRoute, ChildLocation, DangerZone, RoutePoint } from '../types';

interface Props {
  safeRoute?: SafeRoute | null;
  childLocation?: ChildLocation | null;
  dangerZones?: DangerZone[];
  initialRegion?: {
    latitude: number;
    longitude: number;
    latitudeDelta: number;
    longitudeDelta: number;
  };
  showDangerZones?: boolean;
  style?: object;
}

const RISK_COLORS: Record<string, string> = {
  safe: Colors.safe,
  caution: Colors.warning,
  danger: Colors.danger,
};

export default function SafeRouteMap({
  safeRoute,
  childLocation,
  dangerZones = [],
  initialRegion,
  showDangerZones = true,
  style,
}: Props) {
  const routeSegments = useMemo(() => {
    if (!safeRoute?.points || safeRoute.points.length < 2) return [];

    const segments: { points: RoutePoint[]; color: string }[] = [];
    let currentSegment: RoutePoint[] = [safeRoute.points[0]];
    let currentRisk = safeRoute.points[0].riskLevel;

    for (let i = 1; i < safeRoute.points.length; i++) {
      const point = safeRoute.points[i];
      if (point.riskLevel !== currentRisk) {
        currentSegment.push(point);
        segments.push({
          points: currentSegment,
          color: RISK_COLORS[currentRisk] || Colors.safe,
        });
        currentSegment = [point];
        currentRisk = point.riskLevel;
      } else {
        currentSegment.push(point);
      }
    }

    if (currentSegment.length > 1) {
      segments.push({
        points: currentSegment,
        color: RISK_COLORS[currentRisk] || Colors.safe,
      });
    }

    return segments;
  }, [safeRoute]);

  const defaultRegion = initialRegion || {
    latitude: safeRoute?.homeLocation?.latitude || 35.6812,
    longitude: safeRoute?.homeLocation?.longitude || 139.7671,
    latitudeDelta: 0.015,
    longitudeDelta: 0.015,
  };

  return (
    <View style={[styles.container, style]}>
      <MapView
        style={styles.map}
        provider={PROVIDER_DEFAULT}
        initialRegion={defaultRegion}
        showsUserLocation={false}
        showsMyLocationButton={false}
        showsCompass={false}
        mapType="standard"
      >
        {/* Safe route polylines */}
        {routeSegments.map((segment, index) => (
          <Polyline
            key={`route-${index}`}
            coordinates={segment.points.map((p) => ({
              latitude: p.latitude,
              longitude: p.longitude,
            }))}
            strokeColor={segment.color}
            strokeWidth={5}
            lineCap="round"
            lineJoin="round"
          />
        ))}

        {/* Home marker */}
        {safeRoute?.homeLocation && (
          <Marker
            coordinate={{
              latitude: safeRoute.homeLocation.latitude,
              longitude: safeRoute.homeLocation.longitude,
            }}
            title="自宅"
            pinColor={Colors.primary}
          />
        )}

        {/* School marker */}
        {safeRoute?.schoolLocation && (
          <Marker
            coordinate={{
              latitude: safeRoute.schoolLocation.latitude,
              longitude: safeRoute.schoolLocation.longitude,
            }}
            title="学校"
            pinColor={Colors.safe}
          />
        )}

        {/* Child location */}
        {childLocation && (
          <Marker
            coordinate={{
              latitude: childLocation.location.latitude,
              longitude: childLocation.location.longitude,
            }}
            title={childLocation.childName}
            description={childLocation.statusLabel}
          >
            <View style={styles.childMarker}>
              <View style={styles.childMarkerInner} />
            </View>
          </Marker>
        )}

        {/* Danger zones */}
        {showDangerZones &&
          dangerZones.map((zone) => (
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
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    overflow: 'hidden',
  },
  map: {
    flex: 1,
  },
  childMarker: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: Colors.primary + '40',
    justifyContent: 'center',
    alignItems: 'center',
  },
  childMarkerInner: {
    width: 14,
    height: 14,
    borderRadius: 7,
    backgroundColor: Colors.primary,
    borderWidth: 2,
    borderColor: Colors.white,
  },
});
