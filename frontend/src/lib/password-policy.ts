export type PasswordPolicy = {
	min_length: number;
	validators_enabled: boolean;
};

export type PasswordRequirementId = 'min_length' | 'not_numeric' | 'not_similar';

export type PasswordRequirement = {
	id: PasswordRequirementId;
	labelKey: string;
};

export type PasswordProfileContext = {
	username?: string;
	email?: string;
	first_name?: string;
	last_name?: string;
};

export type RequirementStatus = boolean | null;

export function getPasswordRequirements(policy: PasswordPolicy): PasswordRequirement[] {
	const requirements: PasswordRequirement[] = [
		{ id: 'min_length', labelKey: 'auth.password_requirement_min_length' }
	];

	if (policy.validators_enabled) {
		requirements.push(
			{ id: 'not_numeric', labelKey: 'auth.password_requirement_not_numeric' },
			{ id: 'not_similar', labelKey: 'auth.password_requirement_not_similar' }
		);
	}

	return requirements;
}

function isTooSimilar(password: string, profile: PasswordProfileContext): boolean {
	const normalizedPassword = password.toLowerCase();
	if (normalizedPassword.length < 3) {
		return false;
	}

	const attributes = [
		profile.username,
		profile.email?.split('@')[0],
		profile.first_name,
		profile.last_name
	]
		.filter(Boolean)
		.map((value) => value!.toLowerCase().trim())
		.filter((value) => value.length >= 3);

	for (const attribute of attributes) {
		if (
			normalizedPassword === attribute ||
			normalizedPassword.includes(attribute) ||
			attribute.includes(normalizedPassword)
		) {
			return true;
		}
	}

	return false;
}

export function checkPasswordRequirement(
	id: PasswordRequirementId,
	password: string,
	policy: PasswordPolicy,
	profile: PasswordProfileContext = {}
): RequirementStatus {
	if (!password) {
		return null;
	}

	switch (id) {
		case 'min_length':
			return password.length >= policy.min_length;
		case 'not_numeric':
			return !/^\d+$/.test(password);
		case 'not_similar':
			return !isTooSimilar(password, profile);
		default:
			return null;
	}
}

export function passwordsMatch(password: string, confirmPassword: string): RequirementStatus {
	if (!confirmPassword) {
		return null;
	}

	return password === confirmPassword;
}
