import { getServerEndpoint } from '$lib/server/django-proxy';
import { fetchAuthConfig } from '$lib/server/auth-config';
import type { SignupLegalLinks } from '$lib/signup-legal';

export type { SignupLegalLinks };
export { signupLegalRequired } from '$lib/signup-legal';

export async function fetchSignupLegalLinks(
	fetchFn: typeof fetch,
	endpoint = getServerEndpoint()
): Promise<SignupLegalLinks> {
	return (await fetchAuthConfig(fetchFn, endpoint)).legal_links;
}
