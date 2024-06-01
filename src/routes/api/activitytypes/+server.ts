import { addActivityType } from "$lib";
import { db } from "$lib/db/db.server";
import { adventureTable } from "$lib/db/schema";
import type { Adventure } from "$lib/utils/types";
import { json, type RequestEvent, type RequestHandler } from "@sveltejs/kit";
import { and, eq } from "drizzle-orm";

/**
 * Handles the GET request for retrieving activity types based on the provided type parameter.
 * @param {Request} request - The request object containing the URL and locals.
 * @returns {Promise<Response>} - A promise that resolves to the JSON response containing the activity types.
 */
export const GET: RequestHandler = async ({ url, locals }) => {
  const type = url.searchParams.get("type");
  const user = locals.user;

  if (!user) {
    return json({ error: "Unauthorized" }, { status: 401 });
  }

  if (!type) {
    return json({ error: "Missing adventure ID" }, { status: 400 });
  }

  let types = await db
    .select({ activityTypes: adventureTable.activityTypes })
    .from(adventureTable)
    .where(
      and(eq(adventureTable.userId, user.id), eq(adventureTable.type, type))
    )
    .execute();

  types.forEach((type) => {
    console.log(type.activityTypes);
  });
  // if (types.length === 0) {
  //   return json({ error: "Types not found" }, { status: 404 });
  // }

  // console.log(types);

  let array: any[] = [];

  types.forEach((type) => {
    const parsedActivityTypes = type.activityTypes;
    if (parsedActivityTypes && parsedActivityTypes.length > 0) {
      array.push(...parsedActivityTypes);
    }
  });

  // remove duplicates
  array = [...new Set(array)];

  return json({ types: array }, { status: 200 });
};
