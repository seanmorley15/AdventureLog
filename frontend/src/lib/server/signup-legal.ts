import { getServerEndpoint } from '$lib/server/django-proxy';
import type { SignupLegalLinks } from '$lib/signup-legal';

export type { SignupLegalLinks };
export { signupLegalRequired } from '$lib/signup-legal';

const DEFAULT_SIGNUP_LEGAL_LINKS: SignupLegalLinks = {
	terms_of_service_url: null,
	privacy_policy_url: null
};

export async function fetchSignupLegalLinks(
	fetchFn: typeof fetch,
	endpoint = getServerEndpoint()
): Promise<SignupLegalLinks> {
	try {
		const response = await fetchFn(`${endpoint}/auth/signup-legal-links/`);
		if (!response.ok) {
			return DEFAULT_SIGNUP_LEGAL_LINKS;
		}
		return (await response.json()) as SignupLegalLinks;
	} catch {
		return DEFAULT_SIGNUP_LEGAL_LINKS;
	}
}
