import { db } from "$lib/db/db.server";
import {
  adventureTable,
  userPlannedTrips,
  userTable,
  userVisitedWorldTravel,
} from "$lib/db/schema";
import { json, type RequestHandler } from "@sveltejs/kit";
import { eq } from "drizzle-orm";

export const GET: RequestHandler = async ({ locals }): Promise<Response> => {
  if (!locals.user) {
    return json({ error: "Unauthorized" }, { status: 401 });
  }

  const user = await db
    .select()
    .from(userTable)
    .where(eq(userTable.id, locals.user.id));
  if (user.length === 0) {
    return json({ error: "User not found" }, { status: 404 });
  }

  const adventures = await db
    .select()
    .from(adventureTable)
    .where(eq(adventureTable.userId, locals.user.id))
    .execute();

  const trips = await db
    .select()
    .from(userPlannedTrips)
    .where(eq(userPlannedTrips.userId, locals.user.id));

  const worldTravel = await db
    .select()
    .from(userVisitedWorldTravel)
    .where(eq(userVisitedWorldTravel.userId, locals.user.id));

  return json({ user, adventures, trips, worldTravel }, { status: 200 });
};
