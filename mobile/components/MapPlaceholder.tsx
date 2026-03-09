import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Colors } from '../constants';

interface Props {
  style?: object;
  message?: string;
}

export default function MapPlaceholder({ style, message }: Props) {
  return (
    <View style={[styles.container, style]}>
      <Text style={styles.icon}>🗺️</Text>
      <Text style={styles.text}>{message || 'マップはモバイルアプリで表示されます'}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.grayUltraLight,
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: 12,
    padding: 24,
  },
  icon: {
    fontSize: 48,
    marginBottom: 12,
  },
  text: {
    fontSize: 14,
    color: Colors.textSecondary,
    textAlign: 'center',
  },
});
