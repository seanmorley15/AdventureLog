import type { LayoutServerLoad, PageServerLoad } from "./$types";
import { USING_VERCEL } from "$env/static/private";

export const load: LayoutServerLoad = async (event) => {
  if (event.locals.user) {
    return {
      user: event.locals.user,
      isServerSetup: event.locals.isServerSetup,
      usingVercel: USING_VERCEL,
    };
  }
  return {
    user: null,
    isServerSetup: event.locals.isServerSetup,
    usingVercel: USING_VERCEL,
  };
};
