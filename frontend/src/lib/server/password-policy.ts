import { getServerEndpoint } from '$lib/server/django-proxy';
import { fetchAuthConfig } from '$lib/server/auth-config';
import type { PasswordPolicy } from '$lib/password-policy';

export type { PasswordPolicy };

export async function fetchPasswordPolicy(
	fetchFn: typeof fetch,
	endpoint = getServerEndpoint()
): Promise<PasswordPolicy> {
	return (await fetchAuthConfig(fetchFn, endpoint)).password_policy;
}

export function isPasswordLongEnough(
	password: string | null | undefined,
	policy: PasswordPolicy
): boolean {
	return !!password && password.length >= policy.min_length;
}
