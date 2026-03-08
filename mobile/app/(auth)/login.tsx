import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { Colors } from '../../constants';
import { loginWithLine, loginWithApple, loginWithGoogle } from '../../services/auth';

export default function LoginScreen() {
  const [isLoading, setIsLoading] = useState(false);
  const [loadingProvider, setLoadingProvider] = useState<string | null>(null);

  const handleLogin = async (provider: 'line' | 'apple' | 'google') => {
    setIsLoading(true);
    setLoadingProvider(provider);
    try {
      let result;
      switch (provider) {
        case 'line':
          result = await loginWithLine();
          break;
        case 'apple':
          result = await loginWithApple();
          break;
        case 'google':
          result = await loginWithGoogle();
          break;
      }

      if (result) {
        if (result.user.onboardingCompleted) {
          router.replace('/(main)/map');
        } else {
          router.replace('/(onboarding)/home-location');
        }
      }
    } catch (error) {
      Alert.alert(
        'ログインエラー',
        error instanceof Error ? error.message : 'ログインに失敗しました。もう一度お試しください。'
      );
    } finally {
      setIsLoading(false);
      setLoadingProvider(null);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        {/* Logo area */}
        <View style={styles.logoSection}>
          <View style={styles.logoCircle}>
            <Ionicons name="shield-checkmark" size={48} color={Colors.primary} />
          </View>
          <Text style={styles.appName}>Guardian AI</Text>
          <Text style={styles.subtitle}>お子様の通学を{'\n'}AIが見守ります</Text>
        </View>

        {/* Login buttons */}
        <View style={styles.buttonSection}>
          {/* LINE Login - Primary */}
          <TouchableOpacity
            style={[styles.lineButton, isLoading && styles.buttonDisabled]}
            onPress={() => handleLogin('line')}
            disabled={isLoading}
            activeOpacity={0.8}
          >
            {loadingProvider === 'line' ? (
              <ActivityIndicator color="#FFFFFF" />
            ) : (
              <>
                <View style={styles.lineIcon}>
                  <Ionicons name="chatbubble" size={22} color="#FFFFFF" />
                </View>
                <Text style={styles.lineButtonText}>LINEでログイン</Text>
              </>
            )}
          </TouchableOpacity>

          {/* Apple Login */}
          <TouchableOpacity
            style={[styles.secondaryButton, isLoading && styles.buttonDisabled]}
            onPress={() => handleLogin('apple')}
            disabled={isLoading}
            activeOpacity={0.8}
          >
            {loadingProvider === 'apple' ? (
              <ActivityIndicator color={Colors.text} />
            ) : (
              <>
                <Ionicons name="logo-apple" size={20} color={Colors.text} />
                <Text style={styles.secondaryButtonText}>Appleでログイン</Text>
              </>
            )}
          </TouchableOpacity>

          {/* Google Login */}
          <TouchableOpacity
            style={[styles.secondaryButton, isLoading && styles.buttonDisabled]}
            onPress={() => handleLogin('google')}
            disabled={isLoading}
            activeOpacity={0.8}
          >
            {loadingProvider === 'google' ? (
              <ActivityIndicator color={Colors.text} />
            ) : (
              <>
                <Ionicons name="logo-google" size={18} color={Colors.text} />
                <Text style={styles.secondaryButtonText}>Googleでログイン</Text>
              </>
            )}
          </TouchableOpacity>
        </View>

        {/* Footer */}
        <Text style={styles.terms}>
          ログインすることで、利用規約とプライバシーポリシーに{'\n'}同意したものとみなされます。
        </Text>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.white,
  },
  content: {
    flex: 1,
    paddingHorizontal: 24,
    justifyContent: 'center',
  },
  logoSection: {
    alignItems: 'center',
    marginBottom: 60,
  },
  logoCircle: {
    width: 100,
    height: 100,
    borderRadius: 50,
    backgroundColor: Colors.primaryLight,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 20,
  },
  appName: {
    fontSize: 32,
    fontWeight: '800',
    color: Colors.primary,
    letterSpacing: 0.5,
    marginBottom: 10,
  },
  subtitle: {
    fontSize: 17,
    color: Colors.textSecondary,
    textAlign: 'center',
    lineHeight: 26,
  },
  buttonSection: {
    gap: 12,
    marginBottom: 32,
  },
  lineButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.lineGreen,
    borderRadius: 14,
    paddingVertical: 16,
    gap: 10,
  },
  lineIcon: {
    width: 28,
    height: 28,
    justifyContent: 'center',
    alignItems: 'center',
  },
  lineButtonText: {
    fontSize: 17,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  secondaryButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.grayUltraLight,
    borderRadius: 14,
    paddingVertical: 14,
    gap: 10,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  secondaryButtonText: {
    fontSize: 15,
    fontWeight: '600',
    color: Colors.text,
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  terms: {
    fontSize: 11,
    color: Colors.textTertiary,
    textAlign: 'center',
    lineHeight: 18,
  },
});
