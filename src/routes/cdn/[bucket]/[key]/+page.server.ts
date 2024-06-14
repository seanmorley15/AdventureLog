import { redirect } from "@sveltejs/kit";
import type { PageServerLoad, RouteParams } from "../../../$types";
import { getObjectUrl } from "$lib/server/s3";

export const load = (async (event) => {
  const key = event.params.key as string;
  const bucket = event.params.bucket as string;

  const url = getObjectUrl(bucket, key);

  console.log(`Redirecting to ${url}`);

  return redirect(302, url);
}) satisfies PageServerLoad;
