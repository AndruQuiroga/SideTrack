/**
 * @jest-environment node
 */
import { NextRequest } from 'next/server';

describe('recs ranked proxy route', () => {
  const OLD_ENV = process.env;

  beforeEach(() => {
    jest.resetModules();
    process.env = { ...OLD_ENV, NEXT_PUBLIC_API_BASE: 'https://api.example.test' };
  });

  afterEach(() => {
    process.env = OLD_ENV;
    jest.restoreAllMocks();
  });

  it('forwards the request and returns backend JSON unchanged', async () => {
    const { GET } = await import('./route');

    const backendPayload = [
      {
        id: 'track-1',
        title: 'First Track',
      },
    ];

    const fetchMock = jest.spyOn(global, 'fetch');
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify(backendPayload), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    const req = new NextRequest('https://ui.test/api/recs/ranked?new=1', {
      headers: {
        'x-user-id': 'user-123',
        authorization: 'Bearer test-token',
      },
    });

    const res = await GET(req);

    expect(fetchMock).toHaveBeenCalledWith(
      'https://api.example.test/api/v1/recs/ranked?new=1',
      expect.objectContaining({
        method: 'GET',
        headers: expect.objectContaining({
          'X-User-Id': 'user-123',
          Authorization: 'Bearer test-token',
        }),
      }),
    );

    await expect(res.json()).resolves.toEqual(backendPayload);
    expect(res.status).toBe(200);
  });
});

