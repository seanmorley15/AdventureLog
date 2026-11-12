import { describe, expect, it } from 'vitest';
import { canOpenProfile } from './profiles';

const viewer = { uuid: 'me' };

// #1226: a profile page opens when its owner shows it to the viewer.
describe('canOpenProfile', () => {
	it('opens public profiles for everyone', () => {
		expect(canOpenProfile({ uuid: 'a', profile_visibility: 'public' }, null)).toBe(true);
		expect(canOpenProfile({ uuid: 'a', profile_visibility: 'public' }, viewer)).toBe(true);
	});

	it('opens profiles for signed-in users only when the viewer is signed in', () => {
		expect(canOpenProfile({ uuid: 'a', profile_visibility: 'signed_in' }, viewer)).toBe(true);
		expect(canOpenProfile({ uuid: 'a', profile_visibility: 'signed_in' }, null)).toBe(false);
	});

	it('opens a private profile only for its owner', () => {
		expect(canOpenProfile({ uuid: 'a', profile_visibility: 'private' }, viewer)).toBe(false);
		expect(canOpenProfile({ uuid: 'me', profile_visibility: 'private' }, viewer)).toBe(true);
	});

	it('falls back to the old public switch from older servers', () => {
		expect(canOpenProfile({ uuid: 'a', public_profile: true }, null)).toBe(true);
		expect(canOpenProfile({ uuid: 'a', public_profile: false }, viewer)).toBe(false);
	});
});
