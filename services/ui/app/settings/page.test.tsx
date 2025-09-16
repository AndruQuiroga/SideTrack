import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SettingsPage from './page';
import ToastProvider from '../../components/ToastProvider';
import { AuthProvider } from '../../lib/auth';

describe('Settings page', () => {
  beforeEach(() => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      status: 200,
      statusText: 'OK',
      json: () => Promise.resolve({}),
    });
    document.cookie = 'uid=test';
  });

  afterEach(() => {
    jest.resetAllMocks();
  });

  it('shows skeleton while settings data is loading', async () => {
    let resolveFetch: ((value: Response) => void) | undefined;
    (global.fetch as jest.Mock).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveFetch = resolve;
        }),
    );

    render(
      <ToastProvider>
        <AuthProvider>
          <SettingsPage />
        </AuthProvider>
      </ToastProvider>,
    );

    expect(screen.getByRole('status', { name: /loading settings/i })).toBeInTheDocument();

    await waitFor(() => expect(fetch).toHaveBeenCalled());

    resolveFetch?.({
      ok: true,
      status: 200,
      statusText: 'OK',
      json: () => Promise.resolve({}),
    } as unknown as Response);

    await waitFor(() =>
      expect(screen.queryByRole('status', { name: /loading settings/i })).not.toBeInTheDocument(),
    );
  });

  it('pings backend with test button', async () => {
    render(
      <ToastProvider>
        <AuthProvider>
          <SettingsPage />
        </AuthProvider>
      </ToastProvider>,
    );
    const btn = await screen.findByRole('button', { name: /spotify test/i });
    await userEvent.click(btn);
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
  });

  it('reset feedback sends request', async () => {
    render(
      <ToastProvider>
        <AuthProvider>
          <SettingsPage />
        </AuthProvider>
      </ToastProvider>,
    );
    const reset = await screen.findByRole('button', { name: /reset feedback/i });
    await userEvent.click(reset);
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
  });
});

