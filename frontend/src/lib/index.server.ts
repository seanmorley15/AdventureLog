export { backendApiUrl, fetchCSRFToken, getServerEndpoint } from '#lib/server/django-proxy.js';
export {
	buildAuthCookieHeader,
	clearSessionCookie,
	extractSessionIdFromResponse,
	getSessionCookieOptions,
	resolveSessionCookieDomain,
	setSessionFromResponse
} from '#lib/server/session-cookies.js';
export {
	csrfFail,
	djangoBrowserFetch,
	djangoSessionFetch,
	djangoSessionJson,
	requireCsrf,
	CsrfError
} from '#lib/server/django-auth.js';
export { requireUser } from '#lib/server/require-user.js';
export { isPasswordResetSuccess } from '#lib/server/allauth-password-reset.js';
export {
	fetchPasswordPolicy,
	isPasswordLongEnough,
	type PasswordPolicy
} from '#lib/server/password-policy.js';
export {
	fetchAuthConfig,
	DEFAULT_AUTH_CONFIG,
	type AuthConfig,
	type SocialProvider
} from '#lib/server/auth-config.js';
export {
	fetchSignupLegalLinks,
	signupLegalRequired,
	type SignupLegalLinks
} from '#lib/server/signup-legal.js';
export {
	mapAllauthPasswordError,
	mapSignupError,
	type PasswordFormError
} from '#lib/server/password-errors.js';
