import { redirect } from "@sveltejs/kit";
import type { PageServerLoad } from "./$types";
import type { Adventure } from "$lib/utils/types";

export const load: PageServerLoad = async (event) => {
  if (!event.locals.user) {
    return redirect(302, "/login");
  }
  const response = await event.fetch("/api/planner");
  const result = await response.json();
  const activityTypes = await event.fetch("/api/activitytypes?type=planner");
  const activityTypesResult = await activityTypes.json();
  return {
    result,
    activityTypesResult,
  };
};
