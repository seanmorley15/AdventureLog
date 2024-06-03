import { db } from "$lib/db/db.server";
import { adventureTable } from "$lib/db/schema";
import { json, type RequestHandler } from "@sveltejs/kit";
import { ilike, and, eq, arrayContains, or } from "drizzle-orm";

export const GET: RequestHandler = async ({
  url,
  locals,
}): Promise<Response> => {
  const value = url.searchParams.get("value") as string;
  const type = url.searchParams.get("type") as string;
  const user = locals.user;
  const visited = url.searchParams.get("visited");
  let isVisited: boolean | undefined = undefined;
  if (visited === "true") {
    isVisited = true;
  } else if (visited === "false") {
    isVisited = false;
  }

  if (!user) {
    return json({ error: "Unauthorized" }, { status: 401 });
  }
  if (!type) {
    const activityResults = await activitySearch(value, locals, isVisited);
    const locationResults = await locationSearch(value, locals);
    const namesResults = await nameSearch(value, locals);

    return json({
      adventures: [
        ...activityResults.adventures,
        ...locationResults.adventures,
        ...namesResults.adventures,
      ],
    });
  } else if (type === "activity") {
    return json(await activitySearch(value, locals, isVisited));
  } else if (type === "location") {
    return json(await locationSearch(value, locals));
  } else if (type === "name") {
    return json(await nameSearch(value, locals));
  }
  return json({ error: "No results found." }, { status: 400 });
};

async function activitySearch(
  value: string,
  locals: any,
  visited: boolean | undefined
) {
  let arr: string[] = [];
  arr.push(value.toLowerCase());
  let res = await db
    .select()
    .from(adventureTable)
    .where(
      and(
        arrayContains(adventureTable.activityTypes, arr),
        eq(adventureTable.userId, locals.user.id),
        or(
          visited === true ? eq(adventureTable.type, "mylog") : undefined,
          visited === false ? eq(adventureTable.type, "planner") : undefined
        )
      )
    )
    .execute();

  return {
    adventures: res,
  };
}

async function locationSearch(value: string, locals: any) {
  let res = await db
    .select()
    .from(adventureTable)
    .where(
      and(
        ilike(adventureTable.location, `%${value}%`),
        eq(adventureTable.userId, locals.user.id)
      )
    )
    .execute();

  return {
    adventures: res,
  };
}

async function nameSearch(value: string, locals: any) {
  let res = await db
    .select()
    .from(adventureTable)
    .where(
      and(
        ilike(adventureTable.name, `%${value}%`),
        eq(adventureTable.userId, locals.user.id)
      )
    )
    .execute();

  return {
    adventures: res,
  };
}
