import type { PasswordPolicy } from '$lib/password-policy';

type AllauthError = {
	param?: string;
	code?: string;
	message?: string;
};

type AllauthErrorResponse = {
	errors?: AllauthError[];
};

export type PasswordFormError = {
	message: string;
	values?: Record<string, string | number>;
};

const PASSWORD_ERROR_KEYS: Record<string, string> = {
	password_too_short: 'auth.password_too_short',
	password_too_common: 'auth.password_too_common',
	password_entirely_numeric: 'auth.password_entirely_numeric',
	password_too_similar: 'auth.password_too_similar',
	enter_current_password: 'auth.wrong_current_password'
};

export function mapAllauthPasswordError(
	response: AllauthErrorResponse,
	options?: { minLength?: number; fallbackKey?: string }
): PasswordFormError {
	const error = response.errors?.[0];
	const fallback = options?.fallbackKey ?? 'settings.error_change_password';

	if (!error?.code) {
		return { message: fallback };
	}

	const messageKey = PASSWORD_ERROR_KEYS[error.code];
	if (!messageKey) {
		return { message: fallback };
	}

	if (error.code === 'password_too_short') {
		return {
			message: messageKey,
			values: { min: options?.minLength ?? 6 }
		};
	}

	return { message: messageKey };
}

export function mapSignupError(
	response: AllauthErrorResponse,
	policy: PasswordPolicy
): PasswordFormError {
	const passwordError = mapAllauthPasswordError(response, {
		minLength: policy.min_length,
		fallbackKey: 'auth.signup_error'
	});

	if (passwordError.message !== 'auth.signup_error') {
		return passwordError;
	}

	const code = response.errors?.[0]?.code;
	if (code) {
		return { message: `auth.${code}` };
	}

	return { message: 'auth.signup_error' };
}
