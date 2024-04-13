// server laod function
import { db } from '$lib/db/db.server.js';
import { worldTravelCountryRegions } from '$lib/db/schema.js';
import { eq } from 'drizzle-orm';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad  = async ({ params, locals })  => {

  const { countrycode } = params;
    let data = await db
    .select()
    .from(worldTravelCountryRegions)
    .where(eq(worldTravelCountryRegions.country_code, countrycode))
  return {
      regions : data,
  };
}