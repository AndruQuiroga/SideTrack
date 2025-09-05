import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Settings from './page';

describe('Settings page', () => {
  beforeEach(() => {
    global.fetch = jest
      .fn()
      .mockResolvedValue({ ok: true, json: () => Promise.resolve({}) });
  });

  afterEach(() => {
    jest.resetAllMocks();
  });

  it('validates ListenBrainz fields', async () => {
    render(<Settings />);
    const userInput = screen.getByPlaceholderText('ListenBrainz username');
    await userEvent.type(userInput, 'tester');
    await userEvent.click(screen.getByRole('button', { name: /save/i }));
    expect(screen.getByRole('alert')).toHaveTextContent(/listenbrainz user and token required/i);
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

    render(<Settings />);
    await userEvent.type(screen.getByPlaceholderText('ListenBrainz username'), 'lbuser');
    await userEvent.type(screen.getByPlaceholderText('Token'), 'lbtoken');
    await userEvent.type(screen.getByPlaceholderText('Last.fm username'), 'lfmuser');
    await userEvent.type(screen.getByPlaceholderText('API key'), 'lfmkey');
    await userEvent.click(screen.getByLabelText('Use GPU'));
    await userEvent.click(screen.getByLabelText('Extract stems'));
    await userEvent.click(screen.getByLabelText('Use excerpts'));
    await userEvent.click(screen.getByRole('button', { name: /save/i }));

    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
    const body = JSON.parse((fetch as jest.Mock).mock.calls[1][1].body);
    expect(body).toEqual({
      listenBrainzUser: 'lbuser',
      listenBrainzToken: 'lbtoken',
      lastfmUser: 'lfmuser',
      lastfmApiKey: 'lfmkey',
      useGpu: true,
      useStems: true,
      useExcerpts: true,
    });
    expect(await screen.findByRole('status')).toHaveTextContent(/saved/i);
  });
});
