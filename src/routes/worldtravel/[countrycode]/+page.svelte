<script lang="ts">
  export let data;
  import AdventureCard from "$lib/components/AdventureCard.svelte";
  import { getFlag } from "$lib";
  import { goto } from "$app/navigation";
  import { onMount } from "svelte";
  import Us from "$lib/components/maps/US.svelte";
  import WorldTravelCard from "$lib/components/RegionCard.svelte";

  let viewType: String = "cards";

  function markVisited(event: { detail: string }) {
    console.log(`Marked ${event.detail} as visited`);
    fetch("/api/regionvisit", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        region_id: event.detail,
        country_code: data.countrycode,
      }),
    }).then((response) => {
      if (response.status === 401) {
        goto("/login");
      }
      return response.json();
    });
  }

  function removeVisit(event: { detail: string }) {
    console.log(`Removed visit to ${event.detail}`);
    fetch("/api/regionvisit", {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        region_id: event.detail,
      }),
    }).then((response) => {
      if (response.status === 401) {
        goto("/login");
      }
      return response.json();
    });
  }

  function setViewType(type: String) {
    viewType = type;
  }

  onMount(() => {
    console.log(data.visitedRegions);
  });
</script>

<h1 class="text-center text-4xl font-bold">
  Regions in {data.countryName}
  <img
    src={getFlag(40, data.countrycode)}
    class="inline-block -mt-1 mr-1"
    alt="Flag"
  />
</h1>

<div class="join items-center justify-center flex">
  <input
    class="join-item btn btn-neutral"
    type="radio"
    name="viewtype"
    checked
    aria-label="Cards"
    on:click={() => setViewType("cards")}
  />
  <input
    class="join-item btn btn-neutral"
    type="radio"
    name="viewtype"
    aria-label="Map"
    on:click={() => setViewType("map")}
  />
</div>

{#if viewType == "cards"}
  <div class="flex flex-wrap gap-4 mr-4 ml-4 justify-center content-center">
    {#each data.regions as region (region.id)}
      <WorldTravelCard
        countryCode={data.countrycode}
        regionId={region.id}
        name={region.name}
        on:markVisited={markVisited}
        visited={data.visitedRegions.some(
          (visitedRegion) => visitedRegion.region_id === region.id
        )}
        on:removeVisit={removeVisit}
      />
    {/each}
  </div>
{/if}

{#if viewType == "map"}
  {#if data.countrycode.toLowerCase() == "us"}
    <Us on:marked={markVisited} />
  {/if}
{/if}

<svelte:head>
  <title>{data.countryName} Regions | AdventureLog</title>
  <meta
    name="description"
    content="Explore the regions in {data.countryName} and add them to your visited list!"
  />
</svelte:head>
