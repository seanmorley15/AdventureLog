import { db } from "$lib/db/db.server";
import { adventureTable } from "$lib/db/schema";
import { json, type RequestEvent, type RequestHandler } from "@sveltejs/kit";
import { and, eq } from "drizzle-orm";

/**
 * Handles the GET request for retrieving an adventure by ID.
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

  const adventure = await db
    .select()
    .from(adventureTable)
    .where(
      and(
        eq(adventureTable.id, Number(id)), // Convert id to number
        eq(adventureTable.userId, user.id),
        eq(adventureTable.type, "mylog")
      )
    )
    .limit(1)
    .execute();

  if (adventure.length === 0) {
    return json({ error: "Adventure not found" }, { status: 404 });
  }

  //   console.log("GET /api/adventure?id=", id);
  //   console.log("User:", user);

  return json({ adventure }, { status: 200 });
};
