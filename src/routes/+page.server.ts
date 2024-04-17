import { lucia } from "$lib/server/auth";
import { fail, redirect } from "@sveltejs/kit";

import type { Actions, PageServerLoad } from "./$types";

export const load: PageServerLoad = async (event: { locals: { user: any; }; }) => {
  if (event.locals.user)
    return {
      user: event.locals.user,
    };
  return {
    user: null,
  };
};

// handle the logout action
export const actions: Actions = {
  logout: async (event) => {
    if (!event.locals.session) {
      return fail(401);
    }

    await lucia.invalidateSession(event.locals.session.id);
    const sessionCookie = lucia.createBlankSessionCookie();
    event.cookies.set(sessionCookie.name, sessionCookie.value, {
      path: ".",
      ...sessionCookie.attributes,
    });
    return redirect(302, "/login");
  },
  setTheme: async ( { url, cookies }) => {
    const theme = url.searchParams.get("theme");
    // change the theme only if it is one of the allowed themes
    if (theme && ["light", "dark", "night", "retro", "forest"].includes(theme)) {
      cookies.set("colortheme", theme, {
        path: "/",
        maxAge: 60 * 60 * 24 * 365,
      });
    }
  },
};
