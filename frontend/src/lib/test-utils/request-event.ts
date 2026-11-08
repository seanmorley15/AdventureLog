import { vi } from 'vitest';

type CookieJar = Record<string, string>;

export type MockEventOptions = {
	url?: string;
	cookies?: CookieJar;
	headers?: Record<string, string>;
	fetch?: typeof fetch;
};

/**
 * A minimal stand-in for SvelteKit's RequestEvent: enough for hooks and server helpers that
 * read cookies, `locals`, the URL and `event.fetch`. Cookie writes are recorded on `jar`.
 */
export function mockRequestEvent(options: MockEventOptions = {}) {
	const jar: CookieJar = { ...(options.cookies ?? {}) };
	const set = vi.fn((name: string, value: string) => {
		jar[name] = value;
	});
	const del = vi.fn((name: string) => {
		delete jar[name];
	});

	const event = {
		url: new URL(options.url ?? 'http://localhost:8015/'),
		request: new Request(options.url ?? 'http://localhost:8015/', { headers: options.headers }),
		cookies: { get: (name: string) => jar[name], set, delete: del },
		locals: {} as Record<string, unknown>,
		fetch: options.fetch ?? vi.fn()
	};

	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	return { event: event as any, jar, set, delete: del };
}

/** A `resolve` function that records how it was called and returns a canned page. */
export function mockResolve(html = '<html data-theme=""></html>') {
	return vi.fn(
		async (_event: unknown, opts?: { transformPageChunk?: (a: { html: string }) => string }) => {
			const body = opts?.transformPageChunk ? opts.transformPageChunk({ html }) : html;
			return new Response(body, { status: 200 });
		}
	);
}

export function jsonResponse(body: unknown, init: ResponseInit = {}) {
	return new Response(JSON.stringify(body), {
		status: 200,
		headers: { 'content-type': 'application/json' },
		...init
	});
}
