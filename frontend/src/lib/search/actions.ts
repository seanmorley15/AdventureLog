import Calendar from '~icons/mdi/calendar';
import Cog from '~icons/mdi/cog';
import Earth from '~icons/mdi/earth';
import FormatListBulletedSquare from '~icons/mdi/format-list-bulleted-square';
import Map from '~icons/mdi/map';
import MapMarker from '~icons/mdi/map-marker';
import AccountMultiple from '~icons/mdi/account-multiple';
import type { ComponentType } from 'svelte';

export type QuickNavAction = {
	id: string;
	titleKey: string;
	subtitleKey: string;
	url: string;
	icon: ComponentType;
	keywords: string[];
};

export const quickNavActions: QuickNavAction[] = [
	{
		id: 'locations',
		titleKey: 'search.actions.locations',
		subtitleKey: 'search.actions.locations_desc',
		url: '/locations',
		icon: MapMarker,
		keywords: ['adventures', 'locations', 'places']
	},
	{
		id: 'collections',
		titleKey: 'search.actions.collections',
		subtitleKey: 'search.actions.collections_desc',
		url: '/collections',
		icon: FormatListBulletedSquare,
		keywords: ['collections', 'trips']
	},
	{
		id: 'map',
		titleKey: 'search.actions.map',
		subtitleKey: 'search.actions.map_desc',
		url: '/map',
		icon: Map,
		keywords: ['map', 'pins']
	},
	{
		id: 'worldtravel',
		titleKey: 'search.actions.worldtravel',
		subtitleKey: 'search.actions.worldtravel_desc',
		url: '/worldtravel',
		icon: Earth,
		keywords: ['countries', 'regions', 'cities', 'world']
	},
	{
		id: 'calendar',
		titleKey: 'search.actions.calendar',
		subtitleKey: 'search.actions.calendar_desc',
		url: '/calendar',
		icon: Calendar,
		keywords: ['calendar', 'events', 'schedule']
	},
	{
		id: 'users',
		titleKey: 'search.actions.users',
		subtitleKey: 'search.actions.users_desc',
		url: '/users',
		icon: AccountMultiple,
		keywords: ['users', 'profiles', 'community']
	},
	{
		id: 'settings',
		titleKey: 'search.actions.settings',
		subtitleKey: 'search.actions.settings_desc',
		url: '/settings',
		icon: Cog,
		keywords: ['settings', 'preferences', 'account']
	}
];

export function filterQuickNavActions(query: string): QuickNavAction[] {
	const trimmed = query.trim();
	if (!trimmed || trimmed === '>') {
		return quickNavActions;
	}

	const normalized = trimmed.startsWith('>') ? trimmed.slice(1).trim().toLowerCase() : trimmed.toLowerCase();
	if (!normalized) {
		return quickNavActions;
	}

	return quickNavActions.filter((action) =>
		action.keywords.some((keyword) => keyword.includes(normalized) || normalized.includes(keyword))
	);
}
