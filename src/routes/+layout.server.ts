import type { LayoutServerLoad, PageServerLoad } from "./$types";
let USING_VERCEL: string;

try {
  const env = await import("$env/static/private");
  USING_VERCEL = env.USING_VERCEL;
} catch (error) {
  USING_VERCEL = "false";
}

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
