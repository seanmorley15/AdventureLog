import { getServerEndpoint } from '#lib/server/django-proxy.js';
import { fetchAuthConfig } from '#lib/server/auth-config.js';
import type { SignupLegalLinks } from '#lib/signup-legal.js';

export type { SignupLegalLinks };
export { signupLegalRequired } from '#lib/signup-legal.js';

export async function fetchSignupLegalLinks(
	fetchFn: typeof fetch,
	endpoint = getServerEndpoint()
): Promise<SignupLegalLinks> {
	return (await fetchAuthConfig(fetchFn, endpoint)).legal_links;
}
