import { db } from '$lib/db/db.server.js';
import { userVisitedWorldTravel, worldTravelCountryRegions } from '$lib/db/schema.js';
import { and, eq } from 'drizzle-orm';
import type { PageServerLoad } from './$types';
import InfoModal from '$lib/components/InfoModal.svelte';

export const load: PageServerLoad  = async ({ params, locals })  => {
  const { regioncode } = params;
  
    let info = await db
    .select({data: worldTravelCountryRegions})
    .from(worldTravelCountryRegions)
    .where(eq(worldTravelCountryRegions.id, regioncode))
    .limit(1)
    .execute();

    let visited = false;
    if (locals.user) {
      let userVisited = await db
      .select({data: userVisitedWorldTravel})
      .from(userVisitedWorldTravel)
      .where(and(eq(userVisitedWorldTravel.userId, locals.user.id), eq(userVisitedWorldTravel.region_id, regioncode)))
      .limit(1)
      .execute();
      if (userVisited.length !== 0) {
      visited = true;
      }
    }

  return {
      info : info[0],
      visited : visited,
  };
}