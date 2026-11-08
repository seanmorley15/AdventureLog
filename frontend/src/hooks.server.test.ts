import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { authHook, isBackendProxyPath, themeHook, i18nHook } from './hooks.server';
import { jsonResponse, mockRequestEvent, mockResolve } from '#lib/test-utils/request-event.js';

// The hooks are typed against SvelteKit's real Handle; the mocks only carry what they read.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const run = (hook: any, event: unknown, resolve: unknown) => hook({ event, resolve });

beforeEach(() => {
	process.env.PUBLIC_SERVER_URL = 'http://backend.test';
	vi.spyOn(console, 'error').mockImplementation(() => {});
});

afterEach(() => {
	vi.restoreAllMocks();
});

describe('isBackendProxyPath', () => {
	it('matches only /api/ paths', () => {
		expect(isBackendProxyPath('/api/locations/')).toBe(true);
		expect(isBackendProxyPath('/api')).toBe(false);
		expect(isBackendProxyPath('/apiary')).toBe(false);
		expect(isBackendProxyPath('/locations')).toBe(false);
	});
});

describe('authHook', () => {
	it('treats a request with no session cookie as logged out, without calling the backend', async () => {
		const fetchSpy = vi.fn();
		const { event } = mockRequestEvent({ fetch: fetchSpy });
		const resolve = mockResolve();

		await run(authHook, event, resolve);

		expect(event.locals.user).toBeNull();
		expect(fetchSpy).not.toHaveBeenCalled();
		expect(resolve).toHaveBeenCalledOnce();
	});

	it.each(['/api/locations/', '/immich/abc'])(
		'does not look the user up for %s',
		async (pathname) => {
			const fetchSpy = vi.fn();
			const { event } = mockRequestEvent({
				url: `http://localhost:8015${pathname}`,
				cookies: { sessionid: 'abc' },
				fetch: fetchSpy
			});

			await run(authHook, event, mockResolve());

			expect(fetchSpy).not.toHaveBeenCalled();
		}
	);

	it('loads the user and account state from the backend', async () => {
		const fetchSpy = vi.fn().mockResolvedValue(
			jsonResponse({
				user: { uuid: 'u1', username: 'sam' },
				subscription: { plan: 'pro' },
				has_access: false,
				cloud_mode: true,
				pending_invite_count: 2,
				unread_comment_count: 5
			})
		);
		const { event } = mockRequestEvent({
			cookies: { sessionid: 'abc' },
			headers: { cookie: 'sessionid=abc' },
			fetch: fetchSpy
		});

		await run(authHook, event, mockResolve());

		expect(fetchSpy).toHaveBeenCalledWith(
			'http://backend.test/api/account/',
			expect.objectContaining({ headers: { cookie: 'sessionid=abc' } })
		);
		expect(event.locals).toMatchObject({
			user: { uuid: 'u1', username: 'sam' },
			subscription: { plan: 'pro' },
			hasAccess: false,
			cloudMode: true,
			pendingInviteCount: 2,
			unreadCommentCount: 5
		});
	});

	it('defaults to full access when the backend omits the flags', async () => {
		const { event } = mockRequestEvent({
			cookies: { sessionid: 'abc' },
			fetch: vi.fn().mockResolvedValue(jsonResponse({ user: { uuid: 'u1' } }))
		});

		await run(authHook, event, mockResolve());

		expect(event.locals).toMatchObject({ hasAccess: true, cloudMode: false, subscription: null });
	});

	it('clears the session cookie when the backend rejects it', async () => {
		const {
			event,
			delete: del,
			jar
		} = mockRequestEvent({
			cookies: { sessionid: 'expired' },
			fetch: vi.fn().mockResolvedValue(new Response('{}', { status: 401 }))
		});

		await run(authHook, event, mockResolve());

		expect(event.locals.user).toBeNull();
		expect(del).toHaveBeenCalledWith('sessionid', expect.any(Object));
		expect(jar.sessionid).toBeUndefined();
	});

	it.each([429, 500, 502, 503])(
		'keeps the session when the backend is struggling (%i)',
		async (status) => {
			const { event, jar } = mockRequestEvent({
				cookies: { sessionid: 'keepme' },
				fetch: vi.fn().mockResolvedValue(new Response('{}', { status }))
			});

			await run(authHook, event, mockResolve());

			expect(event.locals.user).toBeNull();
			expect(jar.sessionid).toBe('keepme');
		}
	);

	it('keeps the session and still renders on a network error', async () => {
		const { event, jar } = mockRequestEvent({
			cookies: { sessionid: 'keepme' },
			fetch: vi.fn().mockRejectedValue(new TypeError('fetch failed'))
		});
		const resolve = mockResolve();

		await run(authHook, event, resolve);

		expect(event.locals.user).toBeNull();
		expect(jar.sessionid).toBe('keepme');
		expect(resolve).toHaveBeenCalledOnce();
	});

	it('never forwards a csrftoken cookie to the app', async () => {
		const { event, delete: del } = mockRequestEvent({ cookies: { csrftoken: 'x' } });

		await run(authHook, event, mockResolve());

		expect(del).toHaveBeenCalledWith('csrftoken', { path: '/' });
	});
});

describe('themeHook', () => {
	const themed = async (cookies: Record<string, string>, url?: string) => {
		const { event } = mockRequestEvent({ cookies, url });
		const resolve = mockResolve();
		const res = await run(themeHook, event, resolve);
		return res.text();
	};

	it('applies a known theme from the cookie', async () => {
		expect(await themed({ colortheme: 'dark' })).toContain('data-theme="dark"');
	});

	it('lets the ?theme= query parameter win over the cookie', async () => {
		expect(await themed({ colortheme: 'dark' }, 'http://localhost:8015/?theme=light')).toContain(
			'data-theme="light"'
		);
	});

	it('ignores unknown or malicious theme names', async () => {
		for (const bad of ['nope', '"><script>alert(1)</script>', '']) {
			const html = await themed({ colortheme: bad });
			expect(html).toContain('data-theme=""');
			expect(html).not.toContain('<script>');
		}
	});

	it('leaves the page untouched with no theme', async () => {
		expect(await themed({})).toContain('data-theme=""');
	});
});

describe('i18nHook', () => {
	it('exposes the locale cookie on locals', async () => {
		const { event } = mockRequestEvent({ cookies: { locale: 'fr' } });
		await run(i18nHook, event, mockResolve());
		expect(event.locals.locale).toBe('fr');
	});

	it('leaves locals.locale unset with no cookie', async () => {
		const { event } = mockRequestEvent();
		await run(i18nHook, event, mockResolve());
		expect(event.locals.locale).toBeUndefined();
	});
});
