import { redirect } from "@sveltejs/kit";
import type { PageServerLoad, RequestEvent } from "../$types";

export const load: PageServerLoad = async (event: RequestEvent) => {
  if (!event.locals.user) {
    return redirect(302, "/login");
  }
  return {
    user: event.locals.user,
  };
};
