import { apiErrorCode, apiErrorMessage } from '#lib/api/index.js';

/**
 * What to say when `POST /api/locations/{id}/duplicate/` fails. Over the media storage limit
 * (`413 media_quota_exceeded`) gets its own message; anything else says what the server said.
 */
export function duplicateErrorMessage(
	data: unknown,
	messages: { quota: string; fallback: string }
): string {
	if (apiErrorCode(data) === 'media_quota_exceeded') return messages.quota;
	return apiErrorMessage(data, messages.fallback);
}
