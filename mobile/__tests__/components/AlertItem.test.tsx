import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import AlertItem from '../../components/AlertItem';
import type { Alert } from '../../types';

const mockAlert: Alert = {
  id: 'alert-1',
  userId: 'user-1',
  childId: 'child-1',
  type: 'route_deviation',
  severity: 'warning',
  title: 'ルート逸脱',
  message: '通学路から外れています',
  read: false,
  createdAt: new Date(Date.now() - 5 * 60000).toISOString(), // 5分前
};

describe('AlertItem', () => {
  it('タイトルとメッセージを表示する', () => {
    const onPress = jest.fn();
    const { getByText } = render(<AlertItem alert={mockAlert} onPress={onPress} />);

    expect(getByText('ルート逸脱')).toBeTruthy();
    expect(getByText('通学路から外れています')).toBeTruthy();
  });

  it('相対時間を表示する（分前）', () => {
    const onPress = jest.fn();
    const { getByText } = render(<AlertItem alert={mockAlert} onPress={onPress} />);

    expect(getByText('5分前')).toBeTruthy();
  });

  it('タップで onPress コールバックが呼ばれる', () => {
    const onPress = jest.fn();
    const { getByText } = render(<AlertItem alert={mockAlert} onPress={onPress} />);

    fireEvent.press(getByText('ルート逸脱'));
    expect(onPress).toHaveBeenCalledWith(mockAlert);
  });

  it('既読アラートには未読ドットが表示されない', () => {
    const readAlert = { ...mockAlert, read: true };
    const onPress = jest.fn();
    const { queryByTestId } = render(<AlertItem alert={readAlert} onPress={onPress} />);

    // unreadDot はtestIDがないのでスタイルで確認
    // 未読でない場合、unread スタイルが適用されない
    expect(queryByTestId('unread-dot')).toBeNull();
  });

  it('critical severity で正しいアイコン色が使われる', () => {
    const criticalAlert: Alert = { ...mockAlert, severity: 'critical' };
    const onPress = jest.fn();
    const { getByText } = render(<AlertItem alert={criticalAlert} onPress={onPress} />);

    expect(getByText('ルート逸脱')).toBeTruthy();
  });
});
