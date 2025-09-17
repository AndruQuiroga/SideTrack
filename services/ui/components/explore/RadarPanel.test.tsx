import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import RadarPanel from './RadarPanel';
import { apiFetch } from '../../lib/api';

jest.mock('../../lib/api', () => ({
  apiFetch: jest.fn(),
}));

jest.mock('next/dynamic', () => () => () => <div data-testid="mock-radar-chart" />);

describe('RadarPanel', () => {
  const mockApiFetch = apiFetch as jest.MockedFunction<typeof apiFetch>;

  const createResponse = (body: unknown) => ({
    json: () => Promise.resolve(body),
  }) as unknown as Response;

  beforeEach(() => {
    mockApiFetch.mockReset();
    mockApiFetch.mockImplementation((path: string) => {
      if (path.startsWith('/cohorts/influence')) {
        return Promise.resolve(
          createResponse([
            {
              name: 'Artist Alpha',
              type: 'artist',
              score: 0.5,
              confidence: 0.8,
              trend: [0.1, 0.2],
            },
          ]),
        );
      }
      if (path === '/api/dashboard/trajectory') {
        return Promise.resolve(createResponse({ points: [{ week: '2024-01-01' }] }));
      }
      if (path.startsWith('/api/dashboard/radar')) {
        return Promise.resolve(
          createResponse({ week: '2024-01-01', axes: {}, baseline: {} }),
        );
      }
      return Promise.resolve(createResponse({}));
    });
  });

  it('fetches filtered radar data when an influence is selected', async () => {
    const user = userEvent.setup();
    render(<RadarPanel />);

    await screen.findByText('Artist Alpha');

    const initialRadar = mockApiFetch.mock.calls
      .map((call) => call[0])
      .find((url): url is string => typeof url === 'string' && url.startsWith('/api/dashboard/radar?week='));
    expect(initialRadar).toBeDefined();
    if (typeof initialRadar === 'string') {
      expect(initialRadar).not.toContain('cohort=');
    }

    const item = await screen.findByText('Artist Alpha');
    await user.click(item);

    await waitFor(() => {
      const urls = mockApiFetch.mock.calls
        .map((call) => call[0])
        .filter((arg): arg is string => typeof arg === 'string');
      expect(urls.some((url) => url.includes('cohort=artist%3AArtist%20Alpha'))).toBe(true);
    });
  });
});
