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
        created: item.visitedDate,
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

  let res = await db
    .delete(userVisitedAdventures)
    .where(
      and(
        eq(userVisitedAdventures.userId, event.locals.user.id),
        eq(userVisitedAdventures.adventureID, Number(id))
      )
    )
    .execute();

    console.log(res);
    console.log(id);
    console.log(event.locals.user.id);

  return new Response(JSON.stringify({ id: id, res: res }), {
    status: 200,
    headers: {
      "Content-Type": "application/json",
    },
  });
}