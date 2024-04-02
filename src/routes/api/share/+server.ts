import { db } from "$lib/db/db.server";
import { sharedAdventures } from "$lib/db/schema";
import type { Adventure } from "$lib/utils/types";

export async function POST({ request }: { request: Request }) {
  const { key, data } = await request.json();
  let adventure = data as Adventure;
  console.log(adventure);
  await db
    .insert(sharedAdventures)
    .values({ id: key, data: adventure })
    .execute();
  return new Response(JSON.stringify({ key: key }));
}
