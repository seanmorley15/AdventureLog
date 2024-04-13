import { db } from '$lib/db/db.server.js';
import { userVisitedWorldTravel, worldTravelCountryRegions } from '$lib/db/schema.js';
import { eq } from 'drizzle-orm';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad  = async ({ params, locals })  => {

  const { countrycode } = params;
    let data = await db
    .select()
    .from(worldTravelCountryRegions)
    .where(eq(worldTravelCountryRegions.country_code, countrycode))

    let visitedRegions: { id: number; userId: string; region_id: string; }[] = [];
    if (locals.user) {
      visitedRegions = await db
      .select()
      .from(userVisitedWorldTravel)
      .where(eq(userVisitedWorldTravel.userId, locals.user.id))
      .execute();
    }

  return {
      regions : data,
      countrycode: countrycode,
      visitedRegions: visitedRegions,
  };
}