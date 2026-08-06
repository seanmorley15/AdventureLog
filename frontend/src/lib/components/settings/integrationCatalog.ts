export type BuiltinIntegrationDef = {
	id: string;
	nameKey: string;
	descriptionKey: string;
	icon: 'osm' | 'wikipedia' | 'sunrise' | 'overpass';
};

export const BUILTIN_INTEGRATIONS: BuiltinIntegrationDef[] = [
	{
		id: 'nominatim',
		nameKey: 'settings.integrations_hub.builtin.nominatim_name',
		descriptionKey: 'settings.integrations_hub.builtin.nominatim_desc',
		icon: 'osm'
	},
	{
		id: 'wikipedia',
		nameKey: 'settings.integrations_hub.builtin.wikipedia_name',
		descriptionKey: 'settings.integrations_hub.builtin.wikipedia_desc',
		icon: 'wikipedia'
	},
	{
		id: 'sunrise_sunset',
		nameKey: 'settings.integrations_hub.builtin.sunrise_name',
		descriptionKey: 'settings.integrations_hub.builtin.sunrise_desc',
		icon: 'sunrise'
	},
	{
		id: 'overpass',
		nameKey: 'settings.integrations_hub.builtin.overpass_name',
		descriptionKey: 'settings.integrations_hub.builtin.overpass_desc',
		icon: 'overpass'
	}
];
