const timeoutMs = Number.parseInt(process.env.HEALTHCHECK_TIMEOUT_MS ?? '3000', 10);
const urls = (process.env.HEALTHCHECK_URLS ?? 'http://127.0.0.1:3000/healthz')
	.split(',')
	.map((url) => url.trim())
	.filter(Boolean);

for (const url of urls) {
	const controller = new AbortController();
	const timer = setTimeout(() => controller.abort(), timeoutMs);

	try {
		const response = await fetch(url, {
			method: 'GET',
			signal: controller.signal,
			cache: 'no-store'
		});
		if (response.status === 200) {
			process.exit(0);
		}
	} catch (_) {
		// Continue to the next URL.
	} finally {
		clearTimeout(timer);
	}
}

process.exit(1);
