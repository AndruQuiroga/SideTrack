import { render, screen } from '@testing-library/react';

import DaypartHeatmap from './DaypartHeatmap';
import { apiFetch } from '../../lib/api';

jest.mock('../../lib/api', () => ({
  apiFetch: jest.fn(),
}));

jest.mock('react-plotly.js', () => () => <div data-testid="plotly" />);

describe('DaypartHeatmap', () => {
  const mockApiFetch = apiFetch as jest.MockedFunction<typeof apiFetch>;
  const createResponse = (body: unknown) => ({
    json: () => Promise.resolve(body),
  }) as unknown as Response;

  beforeEach(() => {
    mockApiFetch.mockResolvedValue(
      createResponse({
        cells: [
          { day: 0, hour: 5, count: 10, energy: 0.6, valence: 0.7, tempo: 120 },
        ],
        highlights: [{ day: 0, hour: 5, count: 10, z: 1 }],
      }),
    );
  });

  afterEach(() => {
    mockApiFetch.mockReset();
  });

  it('renders highlights from the heatmap response', async () => {
    render(<DaypartHeatmap />);

    expect(await screen.findByText('Mon 5:00 – 10 listens')).toBeInTheDocument();
    expect(mockApiFetch).toHaveBeenCalledWith('/api/dashboard/daypart/heatmap');
  });
});
