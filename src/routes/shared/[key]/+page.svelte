<script lang="ts">
  import type { Adventure } from "$lib/utils/types";
  export let data;
  let array = data.adventureArray as Adventure[];
  import AdventureCard from "$lib/components/AdventureCard.svelte";
</script>

<!-- loop through each adventure -->
<!-- {#each array as adventure}
  <div>
    <h1>{adventure.name}</h1>
    <p>{adventure.location}</p>
    <p>{adventure.created}</p>
    <p>{adventure.id}</p>
  </div>
{/each} -->
<h1 class="text-center font-bold text-4xl">Shared Adventure List</h1>
<div
  class="grid xl:grid-cols-3 lg:grid-cols-3 md:grid-cols-2 sm:grid-cols-1 gap-4 mt-4 content-center auto-cols-auto ml-6 mr-6"
>
  {#each array as adventure (adventure.id)}
    <AdventureCard
      type="shared"
      id={adventure.id}
      name={adventure.name}
      location={adventure.location}
      created={adventure.created}
    />
  {/each}
</div>
