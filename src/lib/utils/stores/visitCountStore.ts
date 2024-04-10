import { writable } from "svelte/store";

let value = 0;
export const visitCount = writable(value);

