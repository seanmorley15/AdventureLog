import { getServerEndpoint } from '$lib/server/django-proxy';
import type { PasswordPolicy } from '$lib/password-policy';

export type { PasswordPolicy };

const DEFAULT_PASSWORD_POLICY: PasswordPolicy = {
	min_length: 6,
	validators_enabled: false
};

export async function fetchPasswordPolicy(
	fetchFn: typeof fetch,
	endpoint = getServerEndpoint()
): Promise<PasswordPolicy> {
	try {
		const response = await fetchFn(`${endpoint}/auth/password-policy/`);
		if (!response.ok) {
			return DEFAULT_PASSWORD_POLICY;
		}
		return (await response.json()) as PasswordPolicy;
	} catch {
		return DEFAULT_PASSWORD_POLICY;
	}
}

export function isPasswordLongEnough(
	password: string | null | undefined,
	policy: PasswordPolicy
): boolean {
	return !!password && password.length >= policy.min_length;
}
