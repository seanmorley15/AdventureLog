import { defineEnvVars } from '@sveltejs/kit/env';

export const variables = defineEnvVars({
	PUBLIC_CARTO_BASEMAP_API_KEY: { public: true, schema: (input) => input ?? '' }
});
