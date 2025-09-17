/**
 * @jest-environment node
 */
import { NextRequest } from 'next/server';

describe('lastfm sync proxy route', () => {
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

    const fetchMock = jest.spyOn(global, 'fetch');
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ detail: 'ok', updated: 12 }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    const req = new NextRequest('https://ui.test/api/lastfm/sync?since=2024-01-01', {
      headers: {
        'x-user-id': 'user-123',
        authorization: 'Bearer test-token',
      },
    });

    const res = await GET(req);

    expect(fetchMock).toHaveBeenCalledWith(
      'https://api.example.test/tags/lastfm/sync?since=2024-01-01',
      expect.objectContaining({
        method: 'GET',
        headers: expect.objectContaining({
          'X-User-Id': 'user-123',
          Authorization: 'Bearer test-token',
        }),
      }),
    );

    await expect(res.json()).resolves.toEqual({ detail: 'ok', updated: 12 });
    expect(res.status).toBe(200);
  });

  it('propagates backend error status codes', async () => {
    const { GET } = await import('./route');

    const fetchMock = jest.spyOn(global, 'fetch');
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ detail: 'something went wrong' }), {
        status: 503,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    const req = new NextRequest('https://ui.test/api/lastfm/sync', {
      headers: {
        'x-user-id': 'user-123',
      },
    });

    const res = await GET(req);

    await expect(res.json()).resolves.toEqual({ detail: 'something went wrong' });
    expect(res.status).toBe(503);
  });
});
