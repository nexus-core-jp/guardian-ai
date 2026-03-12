import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Colors } from '../constants';

const STEP_LABELS = ['お子様情報', '学校選択', 'GPS端末', '確認'];

interface Props {
  currentStep: number;
  totalSteps: number;
}

export default function OnboardingProgress({ currentStep, totalSteps }: Props) {
  return (
    <View style={styles.container}>
      {Array.from({ length: totalSteps }, (_, i) => (
        <View key={i} style={styles.stepContainer}>
          <View
            style={[
              styles.dot,
              i < currentStep ? styles.dotCompleted : i === currentStep ? styles.dotActive : styles.dotInactive,
            ]}
          />
          <Text
            style={[
              styles.label,
              i < currentStep
                ? styles.labelCompleted
                : i === currentStep
                ? styles.labelActive
                : styles.labelInactive,
            ]}
          >
            {STEP_LABELS[i]}
          </Text>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'flex-start',
    gap: 8,
    paddingVertical: 16,
  },
  stepContainer: {
    alignItems: 'center',
    gap: 4,
  },
  dot: {
    height: 8,
    borderRadius: 4,
  },
  dotActive: {
    width: 24,
    backgroundColor: Colors.primary,
  },
  dotCompleted: {
    width: 8,
    backgroundColor: Colors.primary,
  },
  dotInactive: {
    width: 8,
    backgroundColor: Colors.grayLight,
  },
  label: {
    fontSize: 10,
    fontWeight: '600',
  },
  labelActive: {
    color: Colors.primary,
  },
  labelCompleted: {
    color: Colors.primary,
  },
  labelInactive: {
    color: Colors.textTertiary,
  },
});
