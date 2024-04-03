import { lucia } from "$lib/server/auth";
import type { RequestEvent } from "@sveltejs/kit";
import { userVisitedAdventures } from "$lib/db/schema";
import { db } from "$lib/db/db.server";
import { eq } from "drizzle-orm";

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
      result: result,
    }),
    {
      status: 200,
      headers: {
        "Content-Type": "application/json",
      },
    }
  );
}
