// Shared utilities for visit processing across cards
import type { Visit } from '$lib/types';

export interface VisitSummary {
	lastVisit: Visit | null;
	visitCount: number;
	lastVisitDate: string | null;
	lastVisitTimezone: string | null;
}

/**
 * Process visits to get summary information
 * Sorts by start_date DESC (most recent first) to get last visit
 */
export function getVisitSummary(visits: Visit[] | undefined | null): VisitSummary {
	if (!visits || visits.length === 0) {
		return {
			lastVisit: null,
			visitCount: 0,
			lastVisitDate: null,
			lastVisitTimezone: null
		};
	}

	// Sort visits by start_date descending (most recent first)
	const sortedVisits = [...visits].sort((a, b) => {
		const dateA = a.start_date ? new Date(a.start_date).getTime() : 0;
		const dateB = b.start_date ? new Date(b.start_date).getTime() : 0;
		return dateB - dateA;
	});

	const lastVisit = sortedVisits[0];

	return {
		lastVisit,
		visitCount: visits.length,
		lastVisitDate: lastVisit?.start_date ?? null,
		lastVisitTimezone: lastVisit?.timezone ?? null
	};
}

/**
 * Process tags for display (first 3 + remaining count)
 */
export function processTags(tags: string[] | undefined | null): {
	displayTags: string[];
	remainingCount: number;
} {
	if (!tags || tags.length === 0) {
		return { displayTags: [], remainingCount: 0 };
	}

	if (tags.length <= 3) {
		return { displayTags: tags, remainingCount: 0 };
	}

	return {
		displayTags: tags.slice(0, 3),
		remainingCount: tags.length - 3
	};
}
