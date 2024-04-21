import { error, redirect, type Actions, type Handle } from "@sveltejs/kit";
import type { PageServerLoad } from "./$types";
import { db } from "$lib/db/db.server";
import { sessionTable } from "$lib/db/schema";

export const load: PageServerLoad = async (event) => {
  if (!event.locals.user) {
    return redirect(302, "/login");
  } else {
    if (event.locals.user.role !== "admin") {
      return redirect(302, "/settings");
    }
  }
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
