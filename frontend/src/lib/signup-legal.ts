export type SignupLegalLinks = {
	terms_of_service_url: string | null;
	privacy_policy_url: string | null;
};

export function signupLegalRequired(links: SignupLegalLinks): boolean {
	return !!(links.terms_of_service_url || links.privacy_policy_url);
}
