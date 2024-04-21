<script lang="ts">
  import { page } from "$app/stores";
  import type { Adventure } from "$lib/utils/types";
  import { onMount } from "svelte";
  import AdventureCard from "$lib/components/AdventureCard.svelte";

  let plannedAdventures: Adventure[] = [];

  onMount(async () => {
    plannedAdventures = $page.data.plannedAdventures;
    console.log(plannedAdventures);
  });
</script>

<h1 class="font-extrabold text-center text-4xl">My Planned Adventures</h1>

<div
  class="grid xl:grid-cols-3 lg:grid-cols-3 md:grid-cols-2 sm:grid-cols-1 gap-4 mt-4 content-center auto-cols-auto ml-6 mr-6"
>
  {#each plannedAdventures as adventure (adventure.id)}
    <AdventureCard
      type="planner"
      id={adventure.id}
      name={adventure.name}
      location={adventure.location}
      activityTypes={adventure.activityTypes}
      description={adventure?.description}
      date={adventure?.date}
    />
  {/each}
</div>
