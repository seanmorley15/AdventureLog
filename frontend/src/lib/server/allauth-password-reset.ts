/** Detect successful allauth headless password reset (verified but not authenticated). */
export function isPasswordResetSuccess(response: Response, body: unknown): boolean {
	if (response.status === 200) {
		return true;
	}

	if (response.status !== 401 || !body || typeof body !== 'object') {
		return false;
	}

	const payload = body as {
		meta?: { is_authenticated?: boolean };
		data?: { user?: unknown };
	};

	// allauth returns 401 with is_authenticated false after a successful reset.
	return payload.meta?.is_authenticated === false && payload.data?.user != null;
}
