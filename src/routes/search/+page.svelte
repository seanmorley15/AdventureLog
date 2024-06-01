<script lang="ts">
  import AdventureCard from "$lib/components/AdventureCard.svelte";
  import type { Adventure } from "$lib/utils/types";
  import type { PageData } from "./$types";

  export let data: PageData;
  let adventureArray: Adventure[] = data.props?.adventures as Adventure[];
  console.log(adventureArray);
</script>

<main>
  <h1 class="text-center font-bold text-4xl">Search Results</h1>
  {#if adventureArray.length > 0}
    <div
      class="grid xl:grid-cols-3 lg:grid-cols-3 md:grid-cols-2 sm:grid-cols-1 gap-4 mt-4 content-center auto-cols-auto ml-6 mr-6"
    >
      {#each adventureArray as adventure}
        <AdventureCard {adventure} type="mylog" />
      {/each}
    </div>
  {:else}
    <p>No results found</p>
  {/if}
</main>
