import type { Adventure } from "$lib/utils/types";
import { getAdventures } from "./adventureService";

export function exportData() {
  let adventures: Adventure[] = getAdventures();
  let jsonArray = JSON.stringify(adventures);
  console.log(jsonArray);
  let blob = new Blob([jsonArray], { type: "application/json" });
  let url = URL.createObjectURL(blob);
  return url;
}
