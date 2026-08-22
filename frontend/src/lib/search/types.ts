export type SearchEntityType =
	| 'location'
	| 'collection'
	| 'lodging'
	| 'transportation'
	| 'note'
	| 'checklist'
	| 'activity'
	| 'country'
	| 'region'
	| 'city'
	| 'user';

export type SearchHit = {
	type: SearchEntityType;
	id: string;
	title: string;
	subtitle: string;
	url: string;
	score: number;
	meta?: Record<string, unknown>;
};

export type SearchResponse = {
	query: string;
	total: number;
	limit: number;
	offset: number;
	results: SearchHit[];
	facets: Partial<Record<SearchEntityType, number>>;
};

export type SearchTab = 'adventures' | 'places';

import type { QuickNavAction } from './actions';

export type PaletteItem =
	| { kind: 'hit'; hit: SearchHit }
	| { kind: 'place'; id: string; title: string; subtitle: string; url: string }
	| { kind: 'action'; action: QuickNavAction };
