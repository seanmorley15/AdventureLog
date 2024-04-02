import type { Adventure } from "$lib/utils/types";
import { setAdventures } from "./adventureService";

export function importData(file: File) {
  let reader = new FileReader();
  reader.onload = function () {
    let importArray: Adventure[] = JSON.parse(reader.result as string);
    setAdventures(importArray);
  };
  reader.readAsText(file);
}
