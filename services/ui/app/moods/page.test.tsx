import { render } from '@testing-library/react';
import Moods from './page';

describe('Moods page', () => {
  beforeEach(() => {
    global.fetch = jest.fn((url: RequestInfo) => {
      if (typeof url === 'string' && url.includes('/dashboard/trajectory')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ points: [{ week: '2024-06-17' }, { week: '2024-06-24' }] }),
        }) as any;
      }
      if (typeof url === 'string' && url.includes('/dashboard/radar')) {
        const u = new URL(url);
        const week = u.searchParams.get('week');
        return Promise.resolve({
          ok: true,
          json: async () => ({
            week,
            axes: { energy: 0.1, valence: 0.2, danceability: 0.3, brightness: 0.4, pumpiness: 0.5 },
          }),
        }) as any;
      }
      return Promise.resolve({ ok: false }) as any;
    }) as any;
  });

  afterEach(() => {
    (global.fetch as jest.Mock).mockReset();
  });

  it('renders mood shares chart', async () => {
    const { container } = render(await Moods());
    expect(container).toMatchSnapshot();
  });
});
