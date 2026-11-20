import { describe, expect, it } from 'vitest';
import { parseImmichIntegration } from './integrations';

describe('parseImmichIntegration', () => {
	it('reads the Immich web app address (#1117)', () => {
		expect(parseImmichIntegration({ exists: true, web_url: 'https://photos.example.com' })).toEqual(
			{ enabled: true, copyLocally: false, webUrl: 'https://photos.example.com' }
		);
	});

	it('has no address without a connected Immich', () => {
		expect(parseImmichIntegration({ exists: false, web_url: 'https://x' }).webUrl).toBeNull();
		expect(parseImmichIntegration(undefined).webUrl).toBeNull();
		expect(parseImmichIntegration(true)).toEqual({
			enabled: true,
			copyLocally: false,
			webUrl: null
		});
	});
});
