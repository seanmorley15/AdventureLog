// server laod function
import { db } from '$lib/db/db.server.js';
import { worldTravelCountryRegions } from '$lib/db/schema.js';
import { eq } from 'drizzle-orm';

export async function load({ params }) {
  const { countrycode } = params;
    let data = await db
    .select()
    .from(worldTravelCountryRegions)
    .where(eq(worldTravelCountryRegions.country_code, countrycode))
    console.log(data)
  return {
      regions : data,
  };
}