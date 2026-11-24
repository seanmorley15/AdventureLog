/**
 * The message for a visit that could not be saved or removed.
 *
 * A 409 carries the reason from the server, such as a place that is marked visited from another
 * country's page. Any other failure gets the generic message.
 */
export async function visitFailureMessage(res: Response, fallback: string): Promise<string> {
	if (res.status !== 409) return fallback;
	const body = await res.json().catch(() => null);
	return typeof body?.detail === 'string' ? body.detail : fallback;
}

/** A name reduced to its letters and digits, without accents or case, to tell whether two spellings are one. */
function plain(value: string): string {
	return value
		.normalize('NFKD')
		.replace(/[\u0300-\u036f]/g, '')
		.toLowerCase()
		.replace(/[^\p{L}\p{N}]/gu, '');
}

/**
 * The name a place has in its own language, when that is not just the English name again.
 *
 * "Åland" for "Aland Islands" is shown, and "Jersey" for "Jersey" is not.
 */
export function localName(name: string, native?: string | null): string | null {
	const local = native?.trim();
	if (!local) return null;
	return plain(local) === plain(name) ? null : local;
}

/** Whether a search term is found in a place's name or in its name in its own language. */
export function matchesName(term: string, name: string, native?: string | null): boolean {
	const wanted = term.toLowerCase();
	return name.toLowerCase().includes(wanted) || (native ?? '').toLowerCase().includes(wanted);
}
