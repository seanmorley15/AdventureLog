import { db } from "$lib/db/db.server";
import { sharedAdventures } from "$lib/db/schema";
import { eq } from "drizzle-orm";
import type { Adventure } from "$lib/utils/types";

export async function load({ params }) {
  let key = params.key;

  // Fetch data from the database
  let result = await db
    .select()
    .from(sharedAdventures)
    .where(eq(sharedAdventures.id, key))
    .execute();

  // Assuming result is an array with a single object
  let rawData = result[0];

  // Parse the data field, which contains a JSON string
  let adventures = JSON.parse(rawData.data as string);

  // Map the parsed adventures to the Adventure interface
  let adventureArray = adventures.map((item: any) => {
    return {
      id: item.id,
      name: item.name,
      location: item.location,
      created: item.created,
    } as Adventure;
  });


  // Return the array of Adventure objects
  return {
    adventureArray,
  };
}
