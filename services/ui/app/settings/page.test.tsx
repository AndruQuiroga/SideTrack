import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Settings from './page';
import ToastProvider from '../../components/ToastProvider';
import { AuthProvider } from '../../lib/auth';

describe('Settings page', () => {
  beforeEach(() => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({}) });
    document.cookie = 'uid=test';
  });

  afterEach(() => {
    jest.resetAllMocks();
  });

  it('validates ListenBrainz fields', async () => {
    render(
      <ToastProvider>
        <AuthProvider>
          <Settings />
        </AuthProvider>
      </ToastProvider>,
    );
    const userInput = await screen.findByPlaceholderText('ListenBrainz username');
    await userEvent.type(userInput, 'tester');
    await userEvent.click(screen.getByRole('button', { name: /save/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent(
      /listenbrainz user and token required/i,
    );
    // only initial GET
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it('saves settings when valid', async () => {
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({}),
    }); // GET
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ ok: true }),
    }); // POST

    render(
      <ToastProvider>
        <AuthProvider>
          <Settings />
        </AuthProvider>
      </ToastProvider>,
    );
    await userEvent.type(
      await screen.findByPlaceholderText('ListenBrainz username'),
      'lbuser',
    );
    await userEvent.type(
      await screen.findByPlaceholderText('Token'),
      'lbtoken',
    );
    await userEvent.click(await screen.findByLabelText('Use GPU'));
    await userEvent.click(await screen.findByLabelText('Extract stems'));
    await userEvent.click(await screen.findByLabelText('Use excerpts'));
    await userEvent.click(screen.getByRole('button', { name: /save/i }));

    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
    const body = JSON.parse((fetch as jest.Mock).mock.calls[1][1].body);
    expect(body).toEqual({
      listenBrainzUser: 'lbuser',
      listenBrainzToken: 'lbtoken',
      useGpu: true,
      useStems: true,
      useExcerpts: true,
    });
    await waitFor(() =>
      expect(screen.getByRole('status')).toHaveTextContent(/saved/i),
    );
  });
});
