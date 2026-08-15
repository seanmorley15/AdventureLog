export interface AvatarUser {
	first_name?: string | null;
	last_name?: string | null;
	username?: string | null;
}

const AVATAR_GRADIENTS: [string, string][] = [
	['#6366f1', '#8b5cf6'],
	['#0ea5e9', '#06b6d4'],
	['#10b981', '#059669'],
	['#f59e0b', '#d97706'],
	['#ec4899', '#db2777'],
	['#14b8a6', '#0d9488'],
	['#8b5cf6', '#7c3aed'],
	['#ef4444', '#dc2626'],
	['#3b82f6', '#2563eb'],
	['#84cc16', '#65a30d']
];

function hashString(value: string): number {
	let hash = 0;
	for (let i = 0; i < value.length; i += 1) {
		hash = value.charCodeAt(i) + ((hash << 5) - hash);
	}
	return Math.abs(hash);
}

export function getAvatarSeed(user: AvatarUser): string {
	return (
		user.username?.trim() ||
		[user.first_name, user.last_name].filter(Boolean).join(' ').trim() ||
		'?'
	);
}

export function getUserInitials(user: AvatarUser, maxLength = 2): string {
	const first = user.first_name?.trim();
	const last = user.last_name?.trim();

	if (first && last) {
		return `${first[0]}${last[0]}`.toUpperCase();
	}
	if (first) {
		return first.slice(0, maxLength).toUpperCase();
	}

	const username = user.username?.trim();
	if (username) {
		return username.slice(0, maxLength).toUpperCase();
	}

	return '?';
}

export function getAvatarGradient(seed: string): string {
	const [from, to] = AVATAR_GRADIENTS[hashString(seed.toLowerCase()) % AVATAR_GRADIENTS.length];
	return `linear-gradient(135deg, ${from}, ${to})`;
}
