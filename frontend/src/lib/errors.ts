/**
 * How an HTTP status is presented on an error page: which translation keys to use and how
 * serious it looks. The words live in the `errors` section of the locale files.
 */
export type ErrorKind =
	| 'bad_request'
	| 'unauthorized'
	| 'forbidden'
	| 'not_found'
	| 'too_many'
	| 'server'
	| 'unavailable'
	| 'offline'
	| 'generic';

export type ErrorTone = 'info' | 'warning' | 'error';

export function errorKind(status: number | null | undefined, offline = false): ErrorKind {
	if (offline) return 'offline';
	switch (status) {
		case 400:
			return 'bad_request';
		case 401:
			return 'unauthorized';
		case 403:
			return 'forbidden';
		case 404:
		case 410:
			return 'not_found';
		case 429:
			return 'too_many';
		case 500:
			return 'server';
		case 502:
		case 503:
		case 504:
			return 'unavailable';
		default:
			return 'generic';
	}
}

export function errorTone(kind: ErrorKind): ErrorTone {
	switch (kind) {
		case 'server':
		case 'unavailable':
			return 'error';
		case 'not_found':
		case 'bad_request':
		case 'generic':
			return 'info';
		default:
			return 'warning';
	}
}

/** Errors that are worth another try: the same request may succeed in a moment. */
export function isRetryable(kind: ErrorKind): boolean {
	return kind === 'server' || kind === 'unavailable' || kind === 'too_many' || kind === 'offline';
}

/** Messages SvelteKit and the app use by default; they are not worth showing as "details". */
const GENERIC_MESSAGES = new Set([
	'not found',
	'internal error',
	'internal server error',
	'something went wrong',
	'unavailable',
	'error'
]);

export function isGenericMessage(message: string | undefined | null): boolean {
	return !message || GENERIC_MESSAGES.has(message.trim().toLowerCase());
}
