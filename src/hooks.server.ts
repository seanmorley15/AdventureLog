import { lucia } from "$lib/server/auth";
import type { Handle } from "@sveltejs/kit";
import { sequence } from '@sveltejs/kit/hooks';

export const authHook: Handle = async ({ event, resolve }) => {
  const sessionId = event.cookies.get(lucia.sessionCookieName);
  if (!sessionId) {
    event.locals.user = null;
    event.locals.session = null;
    return resolve(event);
  }

  const { session, user } = await lucia.validateSession(sessionId);
  if (session && session.fresh) {
    const sessionCookie = lucia.createSessionCookie(session.id);
    // sveltekit types deviates from the de-facto standard
    // you can use 'as any' too
    event.cookies.set(sessionCookie.name, sessionCookie.value, {
      path: ".",
      ...sessionCookie.attributes,
    });
  }
  if (!session) {
    const sessionCookie:any = lucia.createBlankSessionCookie();
    event.cookies.set(sessionCookie.name, sessionCookie.value, {
      path: ".",
      ...sessionCookie.attributes,
    });
  }
  event.locals.user = user;
  event.locals.session = session;
  return resolve(event);
};

export const themeHook: Handle = async ({ event, resolve }) => {
  let theme:String | null = null;

  const newTheme = event.url.searchParams.get("theme");
  const cookieTheme = event.cookies.get("colortheme");

  if(newTheme) {
    theme = newTheme;
  } else if (cookieTheme) {
    theme = cookieTheme;
  }
  if (theme) {
    return await resolve(event, {
      transformPageChunk: ({ html }) =>
        html.replace('data-theme=""', `data-theme="${theme}"`)
    })
  }

  return await resolve(event);
}

export const handle = sequence(authHook, themeHook);
