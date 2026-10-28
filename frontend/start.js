if (!process.env.ORIGIN && process.env.SITE_URL) {
	process.env.ORIGIN = process.env.SITE_URL;
}

// Node 26+ can hit an undici bug when a client disconnects while a response body
// is still buffered. Suppress that specific crash so the SSR server stays up.
process.on('uncaughtException', (error) => {
	if (
		error &&
		typeof error === 'object' &&
		'code' in error &&
		error.code === 'ERR_ASSERTION' &&
		'message' in error &&
		String(error.message).includes('this.paused')
	) {
		console.warn(
			'[adventurelog] Suppressed undici parser crash; use Node 22 LTS for production:',
			error.message
		);
		return;
	}

	throw error;
});

// adapter-node 6 no longer reads the ORIGIN environment variable (the origin is a
// build-time `paths.origin` option), but AdventureLog images are built once and
// configured at runtime. Keep ORIGIN working by feeding it to the adapter through
// its PROTOCOL_HEADER / HOST_HEADER mechanism using private header names that are
// overwritten on every request, so clients can never spoof them.
const PROTOCOL_HEADER = 'x-adventurelog-origin-protocol';
const HOST_HEADER = 'x-adventurelog-origin-host';

let configuredOrigin = null;
if (process.env.ORIGIN) {
	try {
		const url = new URL(process.env.ORIGIN);
		if (url.protocol !== 'http:' && url.protocol !== 'https:') {
			throw new Error(`unsupported protocol ${url.protocol}`);
		}
		configuredOrigin = { protocol: url.protocol.slice(0, -1), host: url.host };
		process.env.PROTOCOL_HEADER = PROTOCOL_HEADER;
		process.env.HOST_HEADER = HOST_HEADER;
		// The host already carries any non-default port.
		delete process.env.PORT_HEADER;
	} catch (error) {
		console.warn(
			`[adventurelog] Ignoring invalid ORIGIN "${process.env.ORIGIN}": ${error.message}`
		);
	}
}

const { server } = await import('./build/index.js');

if (configuredOrigin) {
	// Runs before the adapter's own request listener, which reads these headers.
	server.prependListener('request', (req) => {
		req.headers[PROTOCOL_HEADER] = configuredOrigin.protocol;
		req.headers[HOST_HEADER] = configuredOrigin.host;
	});
}
