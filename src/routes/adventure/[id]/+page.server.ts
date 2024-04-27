import { redirect } from "@sveltejs/kit";
import type { PageServerLoad } from "./$types";
import { db } from "$lib/db/db.server";
import { and, eq } from "drizzle-orm";
import { adventureTable } from "$lib/db/schema";

export const load = (async (event) => {
  if (!event.locals.user) {
    return redirect(302, "/login");
  }

  let adventureUserId = await db
    .select({ userId: adventureTable.userId })
    .from(adventureTable)
    .where(eq(adventureTable.id, Number(event.params.id)))
    .limit(1)
    .execute();

  console.log(adventureUserId);

  if (
    adventureUserId &&
    adventureUserId[0]?.userId !== event.locals.user.id &&
    adventureUserId !== null
  ) {
    return redirect(302, "/log");
  }

  let adventure = await event.fetch(`/api/adventure?id=${event.params.id}`);

  return { adventure: await adventure.json() };
}) satisfies PageServerLoad;
