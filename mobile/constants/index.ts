export const Colors = {
  primary: '#4A90D9',
  primaryDark: '#3A7BC8',
  primaryLight: '#E6F0FA',
  safe: '#34C759',
  warning: '#FF9500',
  danger: '#FF3B30',
  background: '#F5F5F5',
  white: '#FFFFFF',
  black: '#1A1A1A',
  gray: '#8E8E93',
  grayLight: '#E5E5EA',
  grayUltraLight: '#F2F2F7',
  text: '#1A1A1A',
  textSecondary: '#6B6B6B',
  textTertiary: '#AEAEB2',
  lineGreen: '#06C755',
  border: '#E5E5EA',
  cardShadow: 'rgba(0, 0, 0, 0.08)',
} as const;

export const API_URL = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000';
export const WS_URL = process.env.EXPO_PUBLIC_WS_URL || 'ws://localhost:8000';

export const LINE_CLIENT_ID = process.env.EXPO_PUBLIC_LINE_CLIENT_ID || '';
export const LINE_REDIRECT_URI = process.env.EXPO_PUBLIC_LINE_REDIRECT_URI || 'guardian-ai://auth/callback';

export const GPS_DEVICES = [
  { id: 'bot-talk', name: 'BoTトーク', icon: '🤖' },
  { id: 'mitene', name: 'みてねみまもりGPS', icon: '📍' },
  { id: 'anshin', name: 'あんしんウォッチャー', icon: '👀' },
  { id: 'mamosearch', name: 'まもサーチ', icon: '🔍' },
  { id: 'kids-phone', name: 'キッズケータイ', icon: '📱' },
  { id: 'other', name: 'その他', icon: '📡' },
  { id: 'none', name: '持っていない', icon: '❌' },
] as const;

export const DANGER_TYPES = [
  { id: 'suspicious_person', label: '不審者', icon: '⚠️' },
  { id: 'traffic', label: '交通危険', icon: '🚗' },
  { id: 'dark_road', label: '暗い道', icon: '🌙' },
  { id: 'other', label: 'その他', icon: '📝' },
] as const;

export const RISK_LEVELS = {
  safe: { label: '安全', color: Colors.safe },
  caution: { label: '注意', color: Colors.warning },
  danger: { label: '危険', color: Colors.danger },
} as const;
