import { describe, expect, it } from 'vitest';
import {
	checkPasswordRequirement,
	getPasswordRequirements,
	passwordsMatch,
	type PasswordPolicy
} from './password-policy';

const strict: PasswordPolicy = { min_length: 10, validators_enabled: true };
const lax: PasswordPolicy = { min_length: 6, validators_enabled: false };

describe('getPasswordRequirements', () => {
	it('only requires a minimum length when validators are disabled', () => {
		expect(getPasswordRequirements(lax).map((r) => r.id)).toEqual(['min_length']);
	});

	it('adds numeric and similarity checks when validators are enabled', () => {
		expect(getPasswordRequirements(strict).map((r) => r.id)).toEqual([
			'min_length',
			'not_numeric',
			'not_similar'
		]);
	});
});

describe('checkPasswordRequirement', () => {
	it('returns null (unknown) for an empty password', () => {
		for (const id of ['min_length', 'not_numeric', 'not_similar'] as const) {
			expect(checkPasswordRequirement(id, '', strict)).toBeNull();
		}
	});

	it('checks the minimum length at the boundary', () => {
		expect(checkPasswordRequirement('min_length', '123456789', strict)).toBe(false);
		expect(checkPasswordRequirement('min_length', '1234567890', strict)).toBe(true);
	});

	it('rejects all-numeric passwords', () => {
		expect(checkPasswordRequirement('not_numeric', '12345678901', strict)).toBe(false);
		expect(checkPasswordRequirement('not_numeric', '1234567890a', strict)).toBe(true);
	});

	describe('not_similar', () => {
		const profile = {
			username: 'wanderer',
			email: 'sam.rivers@example.com',
			first_name: 'Samantha'
		};

		it('flags passwords containing profile values, case-insensitively', () => {
			expect(checkPasswordRequirement('not_similar', 'MyWanderer99!', strict, profile)).toBe(false);
			expect(checkPasswordRequirement('not_similar', 'sam.rivers-2027', strict, profile)).toBe(
				false
			);
			expect(checkPasswordRequirement('not_similar', 'xxsamanthaxx', strict, profile)).toBe(false);
		});

		it('flags a password that is a substring of a profile value', () => {
			expect(checkPasswordRequirement('not_similar', 'wander', strict, profile)).toBe(false);
		});

		it('accepts unrelated passwords', () => {
			expect(
				checkPasswordRequirement('not_similar', 'correct-horse-battery', strict, profile)
			).toBe(true);
		});

		it('ignores profile values shorter than 3 characters and very short passwords', () => {
			expect(checkPasswordRequirement('not_similar', 'abcdefgh', strict, { username: 'ab' })).toBe(
				true
			);
			expect(checkPasswordRequirement('not_similar', 'ab', strict, { username: 'abcdef' })).toBe(
				true
			);
		});

		it('works with no profile', () => {
			expect(checkPasswordRequirement('not_similar', 'anything-goes', strict)).toBe(true);
		});
	});
});

describe('passwordsMatch', () => {
	it('is null until the confirmation is typed', () => {
		expect(passwordsMatch('secret', '')).toBeNull();
	});

	it('compares exactly', () => {
		expect(passwordsMatch('secret', 'secret')).toBe(true);
		expect(passwordsMatch('secret', 'Secret')).toBe(false);
	});
});
