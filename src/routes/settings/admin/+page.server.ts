import { error, redirect, type Actions, type Handle } from "@sveltejs/kit";
import type { PageServerLoad } from "./$types";
import { db } from "$lib/db/db.server";
import {
  adventureTable,
  sessionTable,
  userTable,
  userVisitedWorldTravel,
} from "$lib/db/schema";
import type { DatabaseUser } from "$lib/server/auth";
import { count, eq } from "drizzle-orm";

export const load: PageServerLoad = async (event) => {
  let users: DatabaseUser[] = [];
  let visitCount: number = NaN;
  let userCount: number = NaN;
  let regionCount: number = NaN;
  if (!event.locals.user) {
    return redirect(302, "/login");
  }
  if (event.locals.user.role !== "admin") {
    return redirect(302, "/settings");
  }
  if (event.locals.user.role === "admin") {
    users = (await db.select().from(userTable).execute()) as DatabaseUser[];
    visitCount = (await db
      .select({ count: count() })
      .from(adventureTable)
      .where(eq(adventureTable.type, "mylog"))
      .execute()) as unknown as number;
    userCount = (await db
      .select({ count: count() })
      .from(userTable)
      .execute()) as unknown as number;
    regionCount = (await db
      .select({ count: count() })
      .from(userVisitedWorldTravel)
      .execute()) as unknown as number;
  }
  return {
    users,
    visitCount,
    userCount,
    regionCount,
  };
};

export const actions: Actions = {
  clearAllSessions: async (event) => {
    if (event.locals.user && event.locals.user.role !== "admin") {
      return error(403, {
        message: "You are not authorized to perform this action",
      });
    } else {
      console.log("ALL SESSIONS CLEARED by " + event.locals.user?.username);
      await db.delete(sessionTable).execute();
      return {
        status: 200,
        headers: {
          "content-type": "application/json",
        },
        body: JSON.stringify({
          message: "Cleared all sessions",
        }),
      };
    }
  },
};
