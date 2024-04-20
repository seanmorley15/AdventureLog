import type { LayoutServerLoad, PageServerLoad } from "./$types";
let USING_VERCEL: string;
try {
  USING_VERCEL = require("$env/static/private").USING_VERCEL;
} catch (error) {}

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
