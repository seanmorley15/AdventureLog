import type { Database } from 'emoji-picker-element';

let db: Database | null = null;

/** Best emoji for a free-text name, using emoji-picker-element's search data. */
export async function findEmoji(name: string): Promise<string | null> {
	const { Database } = await import('emoji-picker-element');
	db ??= new Database();
	const words = name
		.toLowerCase()
		.split(/[^\p{L}\p{N}]+/u)
		.filter((w) => w.length > 2)
		.sort((a, b) => b.length - a.length);
	for (const q of [name.trim(), ...words]) {
		for (const variant of q.endsWith('s') && q.length > 3 ? [q, q.slice(0, -1)] : [q]) {
			const hit = (await db.getEmojiBySearchQuery(variant)).find((e) => 'unicode' in e);
			if (hit && 'unicode' in hit) return hit.unicode;
		}
	}
	return null;
}

/**
 * Debounced auto-icon for a name/icon form. Only replaces an icon that is empty
 * or was itself auto-filled, so a manual choice is never overwritten.
 */
export function createIconSuggester(getForm: () => { display_name: string; icon: string }) {
	let lastAuto = '';
	let timer: ReturnType<typeof setTimeout> | undefined;
	let seq = 0;

	return function suggest() {
		clearTimeout(timer);
		const name = getForm().display_name.trim();
		const mine = ++seq;
		if (!name) {
			const form = getForm();
			if (form.icon === lastAuto) form.icon = '';
			lastAuto = '';
			return;
		}
		timer = setTimeout(async () => {
			try {
				const emoji = (await findEmoji(name)) ?? '';
				if (mine !== seq) return;
				const form = getForm();
				if (form.icon === '' || form.icon === lastAuto) {
					form.icon = emoji;
					lastAuto = emoji;
				}
			} catch (error) {
				console.error('Emoji suggestion failed', error);
			}
		}, 250);
	};
}
