import type { HandleClientError } from '@sveltejs/kit/hooks';

/**
 * An error nobody planned for, in the browser (a crash while rendering or navigating): the page
 * shows a safe message and a short reference, and the details go to the console under it.
 */
export const handleError: HandleClientError = (input) => {
	if (input.kind !== 'unknown') return;
	const errorId = crypto.randomUUID().slice(0, 8);
	console.error(`[${errorId}] ${input.event.url.pathname}`, input.error);
	return { errorId };
};
