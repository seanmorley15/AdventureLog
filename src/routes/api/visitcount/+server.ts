import type { RequestEvent } from "@sveltejs/kit";
import { count } from "drizzle-orm";
import { eq } from "drizzle-orm";
import { adventureTable } from "$lib/db/schema";
import { db } from "$lib/db/db.server";

export async function GET(event: RequestEvent): Promise<Response> {
  if (!event.locals.user) {
    return new Response(JSON.stringify({ error: "No user found" }), {
      status: 401,
      headers: {
        "Content-Type": "application/json",
      },
    });
  }
  // get the count of the number of adventures the user has visited
  let result = await db
    .select({ count: count() })
    .from(adventureTable)
    .where(eq(adventureTable.userId, event.locals.user.id))
    .execute();

  return new Response(
    JSON.stringify({
      visitCount: result[0].count,
    }),
    {
      status: 200,
      headers: {
        "Content-Type": "application/json",
      },
    }
  );
}
