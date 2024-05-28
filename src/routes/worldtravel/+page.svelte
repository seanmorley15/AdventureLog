<script lang="ts">
  import { goto } from "$app/navigation";
  import { getFlag } from "$lib";
  import AdventureCard from "$lib/components/AdventureCard.svelte";

  export let data: any;

  async function nav(loc: string) {
    goto(`/worldtravel/${loc}`);
  }
</script>

<h1 class="text-center font-bold text-4xl mb-4">Country List</h1>

<div class="flex items-center justify-center flex-wrap">
  {#each data.response as item}
    <button
      class="btn btn-primary mr-2 ml-2 mb-2"
      on:click={() => nav(item.country_code)}
      >{item.name}
      <img
        src={getFlag(24, item.country_code)}
        class="inline-block -mt-1 mr-1"
        alt="Flag"
      /></button
    >
    <!-- <p>Name: {item.name}, Continent: {item.continent}</p> -->
  {/each}
</div>

<svelte:head>
  <title>WorldTravel | AdventureLog</title>
  <meta
    name="description"
    content="Explore the world and add countries to your visited list!"
  />
</svelte:head>
