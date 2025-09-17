import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import InfluencePanel from './InfluencePanel';
import { apiFetch } from '../../lib/api';

type MockResponse = { json: () => Promise<unknown> };

jest.mock('../../lib/api', () => ({
  apiFetch: jest.fn(),
}));

describe('InfluencePanel', () => {
  const mockApiFetch = apiFetch as jest.MockedFunction<typeof apiFetch>;

  beforeEach(() => {
    mockApiFetch.mockResolvedValue({
      json: () =>
        Promise.resolve([
          {
            name: 'Artist Alpha',
            type: 'artist',
            score: 0.5,
            confidence: 0.7,
            trend: [0.1, 0.2],
          },
        ]),
    } as MockResponse as Response);
  });

  afterEach(() => {
    mockApiFetch.mockReset();
  });

  it('invokes onSelect with the cohort value including the type', async () => {
    const onSelect = jest.fn();
    render(<InfluencePanel onSelect={onSelect} />);

    const item = await screen.findByText('Artist Alpha');
    const user = userEvent.setup();
    await user.click(item);

    expect(onSelect).toHaveBeenCalledWith('artist:Artist Alpha');
  });
});
