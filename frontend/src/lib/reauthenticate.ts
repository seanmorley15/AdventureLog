/**
 * Helpers for django-allauth headless reauthentication flows.
 * Sensitive actions (e.g. MFA enable/disable) return 401 with a
 * `reauthenticate` flow when the session is older than REAUTHENTICATION_TIMEOUT.
 */

export async function reauthenticateWithPassword(
	password: string
): Promise<{ ok: boolean; status: number }> {
	const res = await fetch('/auth/browser/v1/auth/reauthenticate', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		credentials: 'include',
		body: JSON.stringify({ password })
	});
	return { ok: res.ok, status: res.status };
}

export function isReauthRequired(res: Response, data: unknown): boolean {
	if (res.status !== 401) return false;
	const body = data as {
		data?: { flows?: { id?: string }[] };
		meta?: { is_authenticated?: boolean };
	} | null;
	const flows = body?.data?.flows ?? [];
	return flows.some((f) => f.id === 'reauthenticate') || body?.meta?.is_authenticated === true;
}
