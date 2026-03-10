import React from 'react';
import { render } from '@testing-library/react-native';
import RiskBadge from '../../components/RiskBadge';

describe('RiskBadge', () => {
  it('安全レベルを正しく表示する', () => {
    const { getByText } = render(<RiskBadge level="safe" />);
    expect(getByText('安全')).toBeTruthy();
  });

  it('注意レベルを正しく表示する', () => {
    const { getByText } = render(<RiskBadge level="caution" />);
    expect(getByText('注意')).toBeTruthy();
  });

  it('危険レベルを正しく表示する', () => {
    const { getByText } = render(<RiskBadge level="danger" />);
    expect(getByText('危険')).toBeTruthy();
  });

  it('smallサイズが適用される', () => {
    const { getByText } = render(<RiskBadge level="safe" size="small" />);
    expect(getByText('安全')).toBeTruthy();
  });
});
