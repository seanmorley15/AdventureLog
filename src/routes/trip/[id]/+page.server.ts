import { redirect } from "@sveltejs/kit";
import type { PageServerLoad } from "./$types";
import { db } from "$lib/db/db.server";
import { and, eq } from "drizzle-orm";
import { adventureTable, userPlannedTrips } from "$lib/db/schema";

export const load: PageServerLoad = (async (event) => {
  if (!event.locals.user) {
    return redirect(302, "/login");
  }

  let adventureUserId: any[] = await db
    .select({ userId: userPlannedTrips.userId })
    .from(userPlannedTrips)
    .where(eq(userPlannedTrips.id, Number(event.params.id)))
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

  let trip = await event.fetch(`/api/trip?id=${event.params.id}`);

  return { trip: await trip.json() };
}) satisfies PageServerLoad;
