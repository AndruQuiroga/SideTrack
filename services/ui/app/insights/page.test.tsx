import { render, screen } from '@testing-library/react';

import InsightsPage from './page';
import { apiFetch } from '../../lib/api';

jest.mock('../../lib/api', () => ({
  apiFetch: jest.fn(),
}));

jest.mock('../../components/insights/InsightModal', () => ({ insight }: { insight: unknown }) => (
  <div data-testid="insight-modal" data-open={insight ? 'true' : 'false'} />
));

describe('InsightsPage', () => {
  const mockApiFetch = apiFetch as jest.MockedFunction<typeof apiFetch>;
  const createResponse = (body: unknown) => ({
    json: () => Promise.resolve(body),
  }) as unknown as Response;

  beforeEach(() => {
    mockApiFetch.mockResolvedValue(
      createResponse([
        {
          ts: '2024-06-01T00:00:00Z',
          type: 'discovery',
          summary: 'Discovered something new',
          severity: 2,
        },
      ]),
    );
  });

  afterEach(() => {
    mockApiFetch.mockReset();
  });

  it('renders insights from the API response', async () => {
    render(<InsightsPage />);

    expect(await screen.findByText('Discovered something new')).toBeInTheDocument();
    expect(mockApiFetch).toHaveBeenCalledWith('/api/dashboard/insights?window=12w');
  });
});
