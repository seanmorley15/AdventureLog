// +page.server.js
import { redirect } from "@sveltejs/kit";
import type { PageServerLoad } from "./$types";
import { db } from "$lib/db/db.server";
import { adventureTable } from "$lib/db/schema";
import { and, eq, arrayContains, ilike } from "drizzle-orm";

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
  } else {
    param = "all";
    value = "";
  }
  // Activity type search
  if (param === "activity") {
    return {
      props: await activitySearch(value, locals),
    };
  }

  if (param === "location") {
    return {
      props: await locationSearch(value, locals),
    };
  }
  if (param === "name") {
    return {
      props: await nameSearch(value, locals),
    };
  }
  if (param == "all" || param == "") {
    console.log("all");
    const activityResults = await activitySearch(value, locals);
    const locationResults = await locationSearch(value, locals);
    const namesResults = await nameSearch(value, locals);

    return {
      props: {
        adventures: [
          ...activityResults.adventures,
          ...locationResults.adventures,
          ...namesResults.adventures,
        ],
      },
    };
  }

  async function activitySearch(value: string, locals: any) {
    let arr: string[] = [];
    arr.push(value.toLowerCase());
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
};
