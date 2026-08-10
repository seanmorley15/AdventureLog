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

await import('./build/index.js');
