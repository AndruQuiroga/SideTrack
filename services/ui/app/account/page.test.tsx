import { render, screen, waitFor } from '@testing-library/react';
import AccountPage from './page';
import ToastProvider from '../../components/ToastProvider';
import { AuthProvider } from '../../lib/auth';

describe('Account page', () => {
  beforeEach(() => {
    global.fetch = jest.fn();
    document.cookie = 'uid=test';
  });

  afterEach(() => {
    jest.resetAllMocks();
  });

  it('shows skeleton while account data is loading', async () => {
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
          <AccountPage />
        </AuthProvider>
      </ToastProvider>,
    );

    expect(screen.getByRole('status', { name: /loading account/i })).toBeInTheDocument();

    await waitFor(() => expect(fetch).toHaveBeenCalled());

    resolveFetch?.({
      ok: true,
      status: 200,
      statusText: 'OK',
      json: () =>
        Promise.resolve({
          user_id: 'test-user',
          lastfmUser: 'tester',
          lastfmConnected: true,
        }),
    } as unknown as Response);

    await waitFor(() =>
      expect(screen.queryByRole('status', { name: /loading account/i })).not.toBeInTheDocument(),
    );
    expect(await screen.findByText(/Logged in as test-user/i)).toBeInTheDocument();
  });
});
