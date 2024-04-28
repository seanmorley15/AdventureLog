import { lucia } from "$lib/server/auth";
import type { RequestEvent } from "@sveltejs/kit";
import { adventureTable } from "$lib/db/schema";
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
    .from(adventureTable)
    .where(eq(adventureTable.userId, event.locals.user.id))
    .execute();
  return new Response(
    // turn the result into an Adventure object array
    JSON.stringify(result.map((r) => r as Adventure)),
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
    .delete(adventureTable)
    .where(
      and(
        eq(adventureTable.userId, event.locals.user.id),
        eq(adventureTable.id, Number(id))
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

  const { newAdventure } = await event.request.json();
  console.log(newAdventure);
  const { name, location, date, description } = newAdventure;

  // insert the adventure to the user's visited list
  await db
    .insert(adventureTable)
    .values({
      userId: event.locals.user.id,
      type: "mylog",
      name: name,
      location: location,
      date: date,
      description: description,
    })
    .execute();
  let res = await db
    .select()
    .from(adventureTable)
    .where(
      and(
        eq(adventureTable.userId, event.locals.user.id),
        eq(adventureTable.name, name),
        eq(adventureTable.location, location),
        eq(adventureTable.date, date),
        eq(adventureTable.description, description)
      )
    )
    .execute();

  // return a response with the adventure object values
  return new Response(
    JSON.stringify({
      adventure: { name, location, date },
      message: { message: "Adventure added" },
      id: res[0].id,
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
  const { newAdventure } = await event.request.json();
  console.log(newAdventure);
  const { name, location, date, id, description } = newAdventure;

  // update the adventure in the user's visited list
  await db
    .update(adventureTable)
    .set({
      name: name,
      location: location,
      date: date,
      description: description,
    })
    .where(
      and(
        eq(adventureTable.userId, event.locals.user.id),
        eq(adventureTable.id, Number(id))
      )
    )
    .execute();

  return new Response(
    JSON.stringify({
      adventure: { id, name, location, date, description },
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
