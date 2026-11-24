/**
 * The shapes every AdventureLog API endpoint shares. See backend/server/API.md.
 *
 * `schema.d.ts` is generated from the backend's OpenAPI document (`pnpm run api:types`).
 * Use `Schemas['Name']` for a response or request body; CI fails when it is stale.
 */

import type { components } from './schema';

/** Every component of the API schema, by name. */
export type Schemas = components['schemas'];

/** `GET /api/account/`: the signed-in user with subscription and header badges. */
export type Account = Schemas['HostedAccount'];

/** `GET /api/server-info/`. */
export type ServerInfo = Schemas['ServerInfo'];

/** `GET /api/places/search/`. */
export type PlaceSearchResponse = Schemas['PlaceSearchResponse'];

/** `GET /api/locations/suggest/`. */
export type LocationSuggestResponse = Schemas['LocationSuggestResponse'];

/** Every error response: a message for people, a stable code for programs, and per-field messages on 400s. */
export type ApiError = Schemas['Error'] & {
	fields?: Schemas['ValidationError']['fields'];
	[extra: string]: unknown;
};

/** `?page=&page_size=` lists. */
export type Paginated<T> = {
	count: number;
	next: string | null;
	previous: string | null;
	results: T[];
};

/** `?limit=&offset=` lists (search and pickers). */
export type LimitOffset<T> = {
	count: number;
	results: T[];
};

/** The message to show for an error response body, or `fallback` when there is none. */
export function apiErrorMessage(data: unknown, fallback: string): string {
	if (!data || typeof data !== 'object') return fallback;
	const body = data as Partial<ApiError>;
	if (typeof body.detail === 'string' && body.detail) return body.detail;
	for (const messages of Object.values(body.fields ?? {})) {
		if (Array.isArray(messages) && typeof messages[0] === 'string') return messages[0];
	}
	return fallback;
}

/** The machine-readable code of an error response body, if it has one. */
export function apiErrorCode(data: unknown): string | null {
	if (!data || typeof data !== 'object') return null;
	const code = (data as Partial<ApiError>).code;
	return typeof code === 'string' ? code : null;
}
