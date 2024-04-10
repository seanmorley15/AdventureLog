import type { RequestEvent } from "@sveltejs/kit";
import { db } from "$lib/db/db.server";
import { eq } from "drizzle-orm";
import { userVisitedAdventures } from "$lib/db/schema";

export async function DELETE(event: RequestEvent): Promise<Response> {
    if (!event.locals.user) {
      return new Response(JSON.stringify({ error: "No user found" }), {
        status: 401,
        headers: {
          "Content-Type": "application/json",
        },
      });
    }
    let res = await db
      .delete(userVisitedAdventures)
      .where(
          eq(userVisitedAdventures.userId, event.locals.user.id),
      )
      .execute();
    return new Response(JSON.stringify({ res: res }), {
      status: 200,
      headers: {
        "Content-Type": "application/json",
      },
    });
  }