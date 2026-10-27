import { getServerEndpoint } from '#lib/server/django-proxy.js';
import type { Schemas } from '#lib/api/index.js';

/** `GET /api/auth/config/`: what the sign-in and sign-up screens need before anyone signs in. */
export type AuthConfig = Schemas['AuthConfig'];

export type SocialProvider = AuthConfig['social_providers'][number];

/** What the screens assume when the server cannot be asked. */
export const DEFAULT_AUTH_CONFIG: AuthConfig = {
	registration: { enabled: true, message: null },
	password_policy: { min_length: 6, validators_enabled: false },
	legal_links: { terms_of_service_url: null, privacy_policy_url: null },
	social_providers: []
};

export async function fetchAuthConfig(
	fetchFn: typeof fetch,
	endpoint = getServerEndpoint()
): Promise<AuthConfig> {
	try {
		const response = await fetchFn(`${endpoint}/api/auth/config/`);
		if (!response.ok) {
			return DEFAULT_AUTH_CONFIG;
		}
		return (await response.json()) as AuthConfig;
	} catch {
		return DEFAULT_AUTH_CONFIG;
	}
}
