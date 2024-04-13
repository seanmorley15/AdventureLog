import { db } from "$lib/db/db.server";
import { sharedAdventures } from "$lib/db/schema";
import type { Adventure } from "$lib/utils/types";

export async function POST({ request, locals }) {
  const { key, data } = await request.json();
  let adventure = data as Adventure;
  console.log(adventure);
  let date = new Date().toISOString().split("T")[0];
  let name = locals.user ? locals.user.username : "Anonymous";
  await db
    .insert(sharedAdventures)
    .values({ id: key, data: adventure, name:name, date:date })
    .execute();
  return new Response(JSON.stringify({ key: key }));
}