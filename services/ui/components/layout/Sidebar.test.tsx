import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import React, { useState } from 'react';

import Sidebar from './Sidebar';

jest.mock('next/navigation', () => ({
  __esModule: true,
  usePathname: () => '/',
}));

jest.mock('next/link', () => ({
  __esModule: true,
  default: React.forwardRef<HTMLAnchorElement, React.ComponentPropsWithoutRef<'a'>>(
    ({ children, ...props }, ref) => (
      <a ref={ref} {...props}>
        {children}
      </a>
    ),
  ),
}));

jest.mock('../common/ThemeToggle', () => ({
  __esModule: true,
  default: () => <div data-testid="theme-toggle" />,
}));

describe('Sidebar', () => {
  beforeEach(() => {
    window.innerWidth = 1024;
    process.env.NEXT_PUBLIC_FEATURE_FLAGS = 'recommendations';
  });

  afterEach(() => {
    delete process.env.NEXT_PUBLIC_FEATURE_FLAGS;
  });

  function SidebarHarness() {
    const [collapsed, setCollapsed] = useState(false);
    return <Sidebar collapsed={collapsed} setCollapsed={setCollapsed} />;
  }

  it('toggles aria-expanded state and label visibility', async () => {
    const user = userEvent.setup();
    render(<SidebarHarness />);

    const toggleButton = screen.getByRole('button', { name: /sidebar/i });
    expect(toggleButton).toHaveAttribute('aria-expanded', 'true');

    const homeLabel = screen.getByText('Home');
    expect(homeLabel).toHaveAttribute('aria-hidden', 'false');

    await user.click(toggleButton);

    expect(toggleButton).toHaveAttribute('aria-expanded', 'false');
    expect(toggleButton).toHaveAccessibleName('Expand sidebar');
    expect(homeLabel).toHaveAttribute('aria-hidden', 'true');
  });
});
