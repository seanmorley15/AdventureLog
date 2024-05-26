import { db } from "$lib/db/db.server";
import { adventureTable, userPlannedTrips } from "$lib/db/schema";
import { error, type RequestEvent } from "@sveltejs/kit";
import { and, eq } from "drizzle-orm";
import type { Trip } from "$lib/utils/types";

export async function POST(event: RequestEvent): Promise<Response> {
  if (!event.locals.user) {
    return new Response(JSON.stringify({ error: "No user found" }), {
      status: 401,
      headers: {
        "Content-Type": "application/json",
      },
    });
  }

  const body = await event.request.json();
  if (!body.newTrip) {
    return error(400, {
      message: "No adventure data provided",
    });
  }

  const { name, description, startDate, endDate } = body.newTrip;

  if (!name) {
    return error(400, {
      message: "Name field is required!",
    });
  }

  // insert the adventure to the user's visited list
  let res = await db
    .insert(userPlannedTrips)
    .values({
      userId: event.locals.user.id,
      name: name,
      description: description || null,
      startDate: startDate || null,
      endDate: endDate || null,
    })
    .returning({ insertedId: userPlannedTrips.id })
    .execute();

  let insertedId = res[0].insertedId;
  console.log(insertedId);

  body.newTrip.id = insertedId;

  return new Response(
    JSON.stringify({
      trip: body.newTrip,
      message: { message: "Trip added" },
      id: insertedId,
    }),
    {
      status: 200,
      headers: {
        "Content-Type": "application/json",
      },
    }
  );
}

export async function GET(event: RequestEvent): Promise<Response> {
  if (!event.locals.user) {
    return new Response(JSON.stringify({ error: "No user found" }), {
      status: 401,
      headers: {
        "Content-Type": "application/json",
      },
    });
  }

  let trips = await db
    .select()
    .from(userPlannedTrips)
    .where(eq(userPlannedTrips.userId, event.locals.user.id))
    .execute();

  return new Response(JSON.stringify(trips), {
    status: 200,
    headers: {
      "Content-Type": "application/json",
    },
  });
}

export async function DELETE(event: RequestEvent): Promise<Response> {
  if (!event.locals.user) {
    return new Response(JSON.stringify({ error: "No user found" }), {
      status: 401,
      headers: {
        "Content-Type": "application/json",
      },
    });
  }

  const body = await event.request.json();
  if (!body.id) {
    return error(400, {
      message: "No trip id provided",
    });
  }

  let deleted = await db
    .delete(adventureTable)
    .where(eq(adventureTable.tripId, body.id))
    .execute();

  let res = await db
    .delete(userPlannedTrips)
    .where(
      and(
        eq(userPlannedTrips.userId, event.locals.user.id),
        eq(userPlannedTrips.id, body.id)
      )
    )
    .execute();

  return new Response(JSON.stringify({ message: "Trip deleted" }), {
    status: 200,
    headers: {
      "Content-Type": "application/json",
    },
  });
}
