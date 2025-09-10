/** @jest-environment node */
import { NextRequest } from 'next/server';
import { middleware } from './middleware';

describe('middleware', () => {
  beforeEach(() => {
    global.fetch = jest.fn();
  });

  afterEach(() => {
    jest.resetAllMocks();
  });

  it('redirects to login and clears cookie when auth check fails', async () => {
    (fetch as jest.Mock).mockResolvedValue({ ok: false });

    const req = new NextRequest('https://example.com/dashboard', {
      headers: { cookie: 'uid=123' },
    });

    const res = await middleware(req);

    expect(fetch).toHaveBeenCalledWith('https://example.com/api/auth/me', {
      headers: { cookie: 'uid=123' },
    });
    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe(
      'https://example.com/login?next=%2Fdashboard',
    );
    expect(res.headers.get('set-cookie') ?? '').toMatch(/uid=;/);
  });
});

