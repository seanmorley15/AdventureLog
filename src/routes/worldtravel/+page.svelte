<script lang="ts">
  import { goto } from "$app/navigation";
  import { getFlag } from "$lib";
  import AdventureCard from "$lib/components/AdventureCard.svelte";
  import CountryCard from "$lib/components/CountryCard.svelte";

  export let data: any;
  console.log(data);
</script>

<h1 class="text-center font-bold text-4xl mb-4">Country List</h1>

<div class="flex flex-wrap gap-4 mr-4 ml-4 justify-center content-center">
  {#each data.response as item}
    <CountryCard countryCode={item.country_code} countryName={item.name} />
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
