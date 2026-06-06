if (!process.env.ORIGIN && process.env.SITE_URL) {
	process.env.ORIGIN = process.env.SITE_URL;
}

await import('./build/index.js');
