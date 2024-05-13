import { db } from "$lib/db/db.server";
import { adventureTable, userPlannedTrips } from "$lib/db/schema";
import type { Adventure, Trip } from "$lib/utils/types";
import { json, type RequestEvent, type RequestHandler } from "@sveltejs/kit";
import { and, eq } from "drizzle-orm";

/**
 * Handles the GET request for retrieving a trip.
 * @param {Request} request - The request object.
 * @param {Response} response - The response object.
 * @returns {Promise<void>} - A promise that resolves when the request is handled.
 */
export const GET: RequestHandler = async ({ url, locals }) => {
  const id = url.searchParams.get("id");
  const user = locals.user;

  if (!user) {
    return json({ error: "Unauthorized" }, { status: 401 });
  }

  if (!id) {
    return json({ error: "Missing adventure ID" }, { status: 400 });
  }

  const trip = await db
    .select()
    .from(userPlannedTrips)
    .where(
      and(
        eq(userPlannedTrips.id, Number(id)), // Convert id to number
        eq(userPlannedTrips.userId, user.id)
      )
    )
    .limit(1)
    .execute();

  if (trip.length === 0) {
    return json({ error: "Trip not found" }, { status: 404 });
  }

  JSON.stringify(
    trip.map((r) => {
      const adventure: Trip = r as Trip;
    })
  );

  //   console.log("GET /api/adventure?id=", id);
  //   console.log("User:", user);

  return json({ trip }, { status: 200 });
};
