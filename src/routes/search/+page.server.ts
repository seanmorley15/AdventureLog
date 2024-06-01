// +page.server.js
import { redirect } from "@sveltejs/kit";
import type { PageServerLoad } from "./$types";
import { db } from "$lib/db/db.server";
import { adventureTable } from "$lib/db/schema";
import { and, eq, arrayContains } from "drizzle-orm";

/**
 * Loads the page data based on the provided URL and locals.
 *
 * @param {PageServerLoadParams} params - The parameters for loading the page.
 * @returns {Promise<PageServerLoadResult>} The result of loading the page.
 */
export const load: PageServerLoad = async ({ url, locals }) => {
  if (!locals.user) {
    return redirect(301, "/login");
  }
  let param: string = "";
  let value: string = "";
  if (Array.from(url.searchParams.entries()).length > 0) {
    const params = Array.from(url.searchParams.entries());
    param = params[0][0];
    value = params[0][1];
  }
  // Activity type search
  if (param === "activity") {
    let arr: string[] = [];
    arr.push(value);
    let res = await db
      .select()
      .from(adventureTable)
      .where(
        and(
          arrayContains(adventureTable.activityTypes, arr),
          eq(adventureTable.userId, locals.user.id)
        )
      )
      .execute();
    console.log(res);

    return {
      props: {
        adventures: res,
      },
    };
  }
};
