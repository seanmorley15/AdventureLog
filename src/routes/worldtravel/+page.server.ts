import { redirect } from "@sveltejs/kit";
import type { PageServerLoad } from "./$types";
import type { Adventure } from "$lib/utils/types";
import { db } from "$lib/db/db.server";
import { worldTravelCountries } from "$lib/db/schema";

export const load: PageServerLoad = async () => {
  // if (!event.locals.user) {
  //   return redirect(302, "/login");
  // }
  let response = await db
  .select()
  .from(worldTravelCountries)

  // let array = result.adventures as Adventure[];
  return {
    response,
  };
};
