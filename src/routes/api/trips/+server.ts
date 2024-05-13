import { db } from "$lib/db/db.server";
import { userPlannedTrips } from "$lib/db/schema";
import { error, type RequestEvent } from "@sveltejs/kit";
import { eq } from "drizzle-orm";

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
      adventures: JSON.stringify([]),
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

  // json parse the adventures into an Adventure array
  for (let trip of trips) {
    if (trip.adventures) {
      trip.adventures = JSON.parse(trip.adventures as unknown as string);
    }
  }

  return new Response(JSON.stringify(trips), {
    status: 200,
    headers: {
      "Content-Type": "application/json",
    },
  });
}
