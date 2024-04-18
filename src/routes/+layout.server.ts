import { goto } from "$app/navigation";
import type { LayoutServerLoad, PageServerLoad } from "./$types";

export const load: LayoutServerLoad = async (event) => {
  if (event.locals.user) {
    return {
      user: event.locals.user,
      isServerSetup: event.locals.isServerSetup,
    };
  }
  return {
    user: null,
    isServerSetup: event.locals.isServerSetup,
  };
};