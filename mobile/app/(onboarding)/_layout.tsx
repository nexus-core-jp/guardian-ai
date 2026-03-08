import React from 'react';
import { Stack } from 'expo-router';

export default function OnboardingLayout() {
  return (
    <Stack
      screenOptions={{
        headerShown: false,
        animation: 'slide_from_right',
      }}
    >
      <Stack.Screen name="home-location" />
      <Stack.Screen name="school-select" />
      <Stack.Screen name="gps-device" />
      <Stack.Screen name="complete" />
    </Stack>
  );
}
