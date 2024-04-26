import type { RequestEvent } from "@sveltejs/kit";
import { db } from "$lib/db/db.server";
import { userVisitedWorldTravel } from "$lib/db/schema";
import { and, eq } from "drizzle-orm";

export async function POST(event: RequestEvent): Promise<Response> {
  if (!event.locals.user) {
    return new Response(JSON.stringify({ error: "Unauthorized" }), {
      status: 401,
      headers: {
        "Content-Type": "application/json",
      },
    });
  }
  let body = await event.request.json();
  let res = await db
    .insert(userVisitedWorldTravel)
    .values({
      userId: event.locals.user.id,
      region_id: body.region_id,
      country_code: body.country_code,
    })
    .execute();
  return new Response(JSON.stringify({ res: res }), {
    status: 200,
    headers: {
      "Content-Type": "application/json",
    },
  });
}

export async function GET(event: RequestEvent): Promise<Response> {
  if (!event.locals.user) {
    return new Response(JSON.stringify({ error: "Unauthorized" }), {
      status: 401,
      headers: {
        "Content-Type": "application/json",
      },
    });
  }
  let res = await db
    .select()
    .from(userVisitedWorldTravel)
    .where(eq(userVisitedWorldTravel.userId, event.locals.user.id));
  return new Response(JSON.stringify({ res: res }), {
    status: 200,
    headers: {
      "Content-Type": "application/json",
    },
  });
}

export async function DELETE(event: RequestEvent): Promise<Response> {
  if (!event.locals.user) {
    return new Response(JSON.stringify({ error: "Unauthorized" }), {
      status: 401,
      headers: {
        "Content-Type": "application/json",
      },
    });
  }
  let body = await event.request.json();
  let res = await db
    .delete(userVisitedWorldTravel)
    .where(
      and(
        eq(userVisitedWorldTravel.userId, event.locals.user.id),
        eq(userVisitedWorldTravel.region_id, body.region_id)
      )
    )
    .execute();
  return new Response(JSON.stringify({ res: res }), {
    status: 200,
    headers: {
      "Content-Type": "application/json",
    },
  });
}
