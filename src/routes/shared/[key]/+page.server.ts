import { db } from "$lib/db/db.server";
import { sharedAdventures } from "$lib/db/schema";
import { eq } from "drizzle-orm";

export async function load({ params }) {
    let key = params.key;
    let result = await db.select().from(sharedAdventures).where(eq(sharedAdventures.id, key)).execute();
    console.log(result);
};