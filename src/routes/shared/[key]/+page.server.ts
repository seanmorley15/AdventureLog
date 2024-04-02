import { db } from "$lib/db/db.server";
import { sharedAdventures } from "$lib/db/schema";
import { eq } from "drizzle-orm";
import type { Adventure } from "$lib/utils/types";

export async function load({ params }) {
  let key = params.key;
  let result = await db
    .select()
    .from(sharedAdventures)
    .where(eq(sharedAdventures.id, key))
    .execute();
  let adventure = result[0].data as Adventure;
  console.log(adventure);
  return {
    result: adventure,
  };
}
