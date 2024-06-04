// +page.server.js
import { redirect } from "@sveltejs/kit";
import type { PageServerLoad } from "./$types";

/**
 * Loads the page data based on the provided URL and locals.
 *
 * @param {PageServerLoadParams} params - The parameters for loading the page.
 * @returns {Promise<PageServerLoadResult>} The result of loading the page.
 */
export const load: PageServerLoad = async ({ url, locals, fetch }) => {
  if (!locals.user) {
    return redirect(301, "/login");
  }
  if (!url.searchParams.has("value")) {
    return { props: { adventures: [] } };
  }
  let data = await fetch("/api/search?value=" + url.searchParams.get("value"));
  let json = await data.json();
  return { props: { adventures: json.adventures } };
};

export const actions = {
  default: async () => {
    console.log("default");
    return { props: {} };
  },
};
