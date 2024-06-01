// +page.server.js
import { error, redirect } from "@sveltejs/kit";
import type { PageServerLoad } from "./$types";
import { db } from "$lib/db/db.server";
import { adventureTable } from "$lib/db/schema";
import { and, eq, arrayContains, inArray } from "drizzle-orm";

export const load: PageServerLoad = async ({ url, locals }) => {
  if (!locals.user) {
    return redirect(301, "/login");
  }

  // db.select().from(posts)
  // .where(arrayContains(posts.tags, ['Typescript', 'ORM']))
  let param: string = "";
  let value: string = "";
  if (Array.from(url.searchParams.entries()).length > 0) {
    const params = Array.from(url.searchParams.entries());
    param = params[0][0];
    value = params[0][1];
  }
  if (param === "activity") {
    let arr: string[] = [];
    arr.push(value);
    let res = await db
      .select()
      .from(adventureTable)
      .where(arrayContains(adventureTable.activityTypes, arr))
      .execute();
    console.log(res);
  }
};
