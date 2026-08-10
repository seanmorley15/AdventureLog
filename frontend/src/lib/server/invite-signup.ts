import type { RequestEvent } from '@sveltejs/kit';
import { djangoSessionFetch } from '$lib/index.server';
import { setSessionFromResponse } from '$lib/server/session-cookies';

export type InviteSignupState = {
	valid: boolean;
	email?: string | null;
	expired?: boolean;
	accepted?: boolean;
	registered?: boolean;
	message?: string | null;
};

/** Read invite key from signup URL query params. */
export function getInviteKeyFromUrl(url: URL): string {
	return (url.searchParams.get('invite_key') || url.searchParams.get('key') || '').trim();
}

/** Validate invite and stash invited email in the Django session for headless signup. */
export async function prepareInviteSignup(
	event: Pick<RequestEvent, 'fetch' | 'cookies'>,
	inviteKey: string
): Promise<InviteSignupState> {
	if (!inviteKey) {
		return { valid: false, message: 'invalid' };
	}

	const inviteRes = await djangoSessionFetch(
		event,
		`/auth/invite-signup/${encodeURIComponent(inviteKey)}/`
	);

	try {
		const inviteData = (await inviteRes.json()) as InviteSignupState;
		if (inviteRes.ok) {
			setSessionFromResponse(event, inviteRes);
			return {
				valid: true,
				email: inviteData.email
			};
		}

		return {
			valid: false,
			email: inviteData.email,
			expired: inviteData.expired,
			accepted: inviteData.accepted,
			registered: inviteData.registered,
			message: inviteData.message
		};
	} catch {
		return { valid: false, message: 'invalid' };
	}
}
