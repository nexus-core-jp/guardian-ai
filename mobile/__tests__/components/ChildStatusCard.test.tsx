import React from 'react';
import { render } from '@testing-library/react-native';
import ChildStatusCard from '../../components/ChildStatusCard';
import type { ChildLocation } from '../../types';

const mockChildLocation: ChildLocation = {
  childId: 'child-1',
  childName: '太郎',
  location: {
    latitude: 35.6762,
    longitude: 139.6503,
    accuracy: 10,
    timestamp: new Date().toISOString(),
    source: 'gps_device',
  },
  status: 'at_school',
  statusLabel: '学校にいます',
  batteryLevel: 75,
};

describe('ChildStatusCard', () => {
  it('ローディング中はローディングメッセージを表示する', () => {
    const { getByText } = render(
      <ChildStatusCard childLocation={null} isLoading={true} />
    );
    expect(getByText('位置情報を取得中...')).toBeTruthy();
  });

  it('データなしの場合はメッセージを表示する', () => {
    const { getByText } = render(
      <ChildStatusCard childLocation={null} isLoading={false} />
    );
    expect(getByText('位置情報がありません')).toBeTruthy();
  });

  it('子どもの名前とステータスを表示する', () => {
    const { getByText } = render(
      <ChildStatusCard childLocation={mockChildLocation} />
    );
    expect(getByText('太郎')).toBeTruthy();
    expect(getByText('学校にいます')).toBeTruthy();
  });

  it('バッテリーレベルを表示する', () => {
    const { getByText } = render(
      <ChildStatusCard childLocation={mockChildLocation} />
    );
    expect(getByText('75%')).toBeTruthy();
  });

  it('バッテリーなしの場合はバッテリー表示がない', () => {
    const noBattery = { ...mockChildLocation, batteryLevel: undefined };
    const { queryByText } = render(
      <ChildStatusCard childLocation={noBattery} />
    );
    expect(queryByText('%')).toBeNull();
  });

  it('移動中ステータスを表示する', () => {
    const moving = {
      ...mockChildLocation,
      status: 'moving' as const,
      statusLabel: '移動中',
    };
    const { getByText } = render(
      <ChildStatusCard childLocation={moving} />
    );
    expect(getByText('移動中')).toBeTruthy();
  });
});
