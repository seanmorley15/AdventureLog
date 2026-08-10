import AccountMultiple from '~icons/mdi/account-multiple';
import Airplane from '~icons/mdi/airplane';
import Bed from '~icons/mdi/bed';
import Checklist from '~icons/mdi/clipboard-list-outline';
import Earth from '~icons/mdi/earth';
import FormatListBulletedSquare from '~icons/mdi/format-list-bulleted-square';
import MapMarker from '~icons/mdi/map-marker';
import MapMarkerRadius from '~icons/mdi/map-marker-radius';
import NoteText from '~icons/mdi/note-text-outline';
import Run from '~icons/mdi/run';
import type { ComponentType } from 'svelte';
import type { SearchEntityType } from './types';

const searchTypeIcons: Record<SearchEntityType, ComponentType> = {
	location: MapMarker,
	collection: FormatListBulletedSquare,
	lodging: Bed,
	transportation: Airplane,
	note: NoteText,
	checklist: Checklist,
	activity: Run,
	country: Earth,
	region: MapMarkerRadius,
	city: MapMarkerRadius,
	user: AccountMultiple
};

export function getSearchTypeIcon(type: SearchEntityType): ComponentType {
	return searchTypeIcons[type] || MapMarker;
}
