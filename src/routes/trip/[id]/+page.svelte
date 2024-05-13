<script lang="ts">
  import type { Adventure, Trip } from "$lib/utils/types";
  import { onMount } from "svelte";
  import type { PageData } from "./$types";
  import { goto } from "$app/navigation";

  export let data: PageData;

  let trip: Trip | null = null;

  onMount(() => {
    if (data.trip.trip) {
      trip = data.trip.trip[0];
    } else {
      goto("/404");
    }
  });
</script>

<main>
  {#if trip}
    <h1>{trip.name}</h1>
    <p>{trip.description}</p>
    <p>{trip.startDate}</p>
    <p>{trip.endDate}</p>
  {/if}
</main>
