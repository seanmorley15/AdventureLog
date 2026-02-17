/**
 * Shared filter state type for list pages
 * Used by: /locations, /transportations, /lodging, /collections
 */
export interface FilterState {
	order_by: string;
	order: 'asc' | 'desc' | string;
	is_visited: 'all' | 'visited' | 'not_visited' | string;
	is_public: 'all' | 'public' | 'private' | string;
	ownership: 'all' | 'mine' | 'public' | string;
	min_rating: 'all' | '1' | '2' | '3' | '4' | '5' | string;
}

/**
 * Default filter state
 */
export const DEFAULT_FILTER_STATE: FilterState = {
	order_by: 'updated_at',
	order: 'desc',
	is_visited: 'all',
	is_public: 'all',
	ownership: 'all',
	min_rating: 'all'
};

/**
 * Pagination state
 */
export interface PaginationState {
	currentPage: number;
	totalPages: number;
	count: number;
	resultsPerPage: number;
}

/**
 * Create default pagination state
 */
export function createPaginationState(count: number, resultsPerPage: number = 25): PaginationState {
	return {
		currentPage: 1,
		totalPages: Math.ceil(count / resultsPerPage),
		count,
		resultsPerPage
	};
}
