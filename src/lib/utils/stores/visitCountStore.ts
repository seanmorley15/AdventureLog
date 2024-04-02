import { onMount } from "svelte";
import { writable } from "svelte/store";

export const visitCount = writable(0);
