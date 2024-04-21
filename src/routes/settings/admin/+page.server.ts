import { error, redirect, type Actions, type Handle } from "@sveltejs/kit";
import type { PageServerLoad } from "./$types";
import { db } from "$lib/db/db.server";
import { sessionTable, userTable } from "$lib/db/schema";
import type { DatabaseUser } from "$lib/server/auth";

export const load: PageServerLoad = async (event) => {
  let users: DatabaseUser[] = [];
  if (!event.locals.user) {
    return redirect(302, "/login");
  }
  if (event.locals.user.role !== "admin") {
    return redirect(302, "/settings");
  }
  if (event.locals.user.role === "admin") {
    users = (await db.select().from(userTable).execute()) as DatabaseUser[];
    console.log(users);
  }
  return {
    users,
  };
};

export const actions: Actions = {
  clearAllSessions: async (event) => {
    if (event.locals.user && event.locals.user.role !== "admin") {
      return error(403, {
        message: "You are not authorized to perform this action",
      });
    } else {
      console.log("ALL SESSIONS CLEARED");
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
