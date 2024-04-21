import { lucia } from "$lib/server/auth";
import type { RequestEvent } from "@sveltejs/kit";
import { userVisitedAdventures } from "$lib/db/schema";
import { db } from "$lib/db/db.server";
import { and, eq } from "drizzle-orm";
import type { Adventure } from "$lib/utils/types";

// Gets all the adventures that the user has visited
export async function GET(event: RequestEvent): Promise<Response> {
  if (!event.locals.user) {
    return new Response(JSON.stringify({ error: "No user found" }), {
      status: 401,
      headers: {
        "Content-Type": "application/json",
      },
    });
  }
  let result = await db
    .select()
    .from(userVisitedAdventures)
    .where(eq(userVisitedAdventures.userId, event.locals.user.id))
    .execute();
  return new Response(
    JSON.stringify({
      adventures: result.map((item) => ({
        id: item.adventureID,
        name: item.adventureName,
        location: item.location,
        date: item.visitedDate,
      })),
    }),
    {
      status: 200,
      headers: {
        "Content-Type": "application/json",
      },
    }
  );
}

// deletes the adventure given the adventure id and the user object
export async function DELETE(event: RequestEvent): Promise<Response> {
  if (!event.locals.user) {
    return new Response(JSON.stringify({ error: "No user found" }), {
      status: 401,
      headers: {
        "Content-Type": "application/json",
      },
    });
  }

  // get id from the body
  const { id } = await event.request.json();

  if (!id) {
    return new Response(JSON.stringify({ error: "No id found" }), {
      status: 400,
      headers: {
        "Content-Type": "application/json",
      },
    });
  }

  let res = await db
    .delete(userVisitedAdventures)
    .where(
      and(
        eq(userVisitedAdventures.userId, event.locals.user.id),
        eq(userVisitedAdventures.adventureID, Number(id))
      )
    )
    .execute();

  return new Response(JSON.stringify({ id: id, res: res }), {
    status: 200,
    headers: {
      "Content-Type": "application/json",
    },
  });
}

// add the adventure to the user's visited list
export async function POST(event: RequestEvent): Promise<Response> {
  if (!event.locals.user) {
    return new Response(JSON.stringify({ error: "No user found" }), {
      status: 401,
      headers: {
        "Content-Type": "application/json",
      },
    });
  }

  // get properties from the body
  const { name, location, date } = await event.request.json();

  // insert the adventure to the user's visited list
  await db
    .insert(userVisitedAdventures)
    .values({
      userId: event.locals.user.id,
      adventureName: name,
      location: location,
      visitedDate: date,
    })
    .execute();
  let res = await db
    .select()
    .from(userVisitedAdventures)
    .where(
      and(
        eq(userVisitedAdventures.userId, event.locals.user.id),
        eq(userVisitedAdventures.adventureName, name),
        eq(userVisitedAdventures.location, location),
        eq(userVisitedAdventures.visitedDate, date)
      )
    )
    .execute();

  // return a response with the adventure object values
  return new Response(
    JSON.stringify({
      adventure: { name, location, date },
      message: { message: "Adventure added" },
      id: res[0].adventureID,
    }),
    {
      status: 200,
      headers: {
        "Content-Type": "application/json",
      },
    }
  );
}

// put route to update existing adventure
export async function PUT(event: RequestEvent): Promise<Response> {
  if (!event.locals.user) {
    return new Response(JSON.stringify({ error: "No user found" }), {
      status: 401,
      headers: {
        "Content-Type": "application/json",
      },
    });
  }

  // get properties from the body
  const { id, name, location, date } = await event.request.json();

  // update the adventure in the user's visited list
  await db
    .update(userVisitedAdventures)
    .set({
      adventureName: name,
      location: location,
      visitedDate: date,
    })
    .where(
      and(
        eq(userVisitedAdventures.userId, event.locals.user.id),
        eq(userVisitedAdventures.adventureID, Number(id))
      )
    )
    .execute();

  return new Response(
    JSON.stringify({
      adventure: { id, name, location, date },
      message: { message: "Adventure updated" },
    }),
    {
      status: 200,
      headers: {
        "Content-Type": "application/json",
      },
    }
  );
}
