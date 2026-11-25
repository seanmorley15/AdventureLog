import { describe, expect, it } from 'vitest';
import { duplicateErrorMessage } from './location-duplicate';

const messages = { quota: 'Over your storage', fallback: 'Failed' };

describe('duplicateErrorMessage', () => {
	it('names the storage limit for media_quota_exceeded', () => {
		const body = { detail: 'Storage full.', code: 'media_quota_exceeded', limit_bytes: 10 };
		expect(duplicateErrorMessage(body, messages)).toBe('Over your storage');
	});

	it("shows the server's message for other errors", () => {
		expect(duplicateErrorMessage({ detail: 'Not found.', code: 'not_found' }, messages)).toBe(
			'Not found.'
		);
	});

	it('falls back when there is no body', () => {
		expect(duplicateErrorMessage(null, messages)).toBe('Failed');
	});
});
