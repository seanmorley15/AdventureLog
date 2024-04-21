import { db } from "$lib/db/db.server";
import { userPlannedAdventures } from "$lib/db/schema";
import { eq } from "drizzle-orm";
import type { LayoutServerLoad } from "../$types";
import { redirect } from "@sveltejs/kit";

export const load: LayoutServerLoad = async (event) => {
  if (event.locals.user) {
    let plannedAdventures = await db
      .select()
      .from(userPlannedAdventures)
      .where(eq(userPlannedAdventures.userId, event.locals.user.id));
    return {
      user: event.locals.user,
      isServerSetup: event.locals.isServerSetup,
      plannedAdventures,
    };
  } else {
    return redirect(302, "/login");
  }
};
