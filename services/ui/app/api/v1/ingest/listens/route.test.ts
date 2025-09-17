/**
 * @jest-environment node
 */
import { NextRequest } from 'next/server';

describe('ingest listens proxy route', () => {
  const OLD_ENV = process.env;

  beforeEach(() => {
    jest.resetModules();
    process.env = { ...OLD_ENV, NEXT_PUBLIC_API_BASE: 'https://api.example.test' };
  });

  afterEach(() => {
    process.env = OLD_ENV;
    jest.restoreAllMocks();
  });

  it('forwards POST requests with auth and body to the backend', async () => {
    const { POST } = await import('./route');

    const payload = { listens: [] };
    const fetchMock = jest.spyOn(global, 'fetch');
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ detail: 'ok', ingested: 1 }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    const req = new NextRequest(
      'https://ui.test/api/v1/ingest/listens?source=lastfm&since=2025-09-10',
      {
        method: 'POST',
        headers: {
          'x-user-id': 'user-123',
          authorization: 'Bearer test-token',
          'content-type': 'application/json',
        },
        body: JSON.stringify(payload),
      },
    );

    const res = await POST(req);

    expect(fetchMock).toHaveBeenCalledWith(
      'https://api.example.test/api/v1/ingest/listens?source=lastfm&since=2025-09-10',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          'X-User-Id': 'user-123',
          Authorization: 'Bearer test-token',
          'Content-Type': 'application/json',
        }),
        body: JSON.stringify(payload),
      }),
    );

    await expect(res.json()).resolves.toEqual({ detail: 'ok', ingested: 1 });
    expect(res.status).toBe(200);
  });
});
