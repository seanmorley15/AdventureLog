import { error, redirect, type Actions } from "@sveltejs/kit";
import type { PageServerLoad } from "./$types";

export const load: PageServerLoad = async (event) => {
  if (!event.locals.user) {
    return redirect(302, "/login");
  } else {
    if (event.locals.user.role !== "admin") {
      return redirect(302, "/settings");
    }
  }
};
