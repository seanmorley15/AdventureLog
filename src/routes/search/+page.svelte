<script lang="ts">
  import { enhance } from "$app/forms";
  import AdventureCard from "$lib/components/AdventureCard.svelte";
  import type { Adventure } from "$lib/utils/types";
  import type { SubmitFunction } from "@sveltejs/kit";
  import type { PageData } from "./$types";

  let typeValue: string = "";
  let visitedValue: string = "all";

  async function filterResults() {
    console.log(typeValue);
    console.log(visitedValue);

    if (!typeValue) {
      typeValue = "";
    }
    const value = new URLSearchParams(location.search).get("value");
    console.log(value);
    console.log(
      `/api/search?value=${value}&type=${typeValue}&visited=${visitedValue}`
    );
    let data = await fetch(
      `/api/search?value=${value}&type=${typeValue}&visited=${visitedValue}`
    );
    console.log(data);
    adventureArray = [];
    let res = await data.json();
    adventureArray = res.adventures as Adventure[];
  }

  export let data: PageData;
  let adventureArray: Adventure[] = data.props?.adventures as Adventure[];

  const filter: SubmitFunction = async ({ formData }) => {
    const radioValue = formData.get("visited") as string;
    let typeValue = formData.get("type") as string;
    if (!typeValue) {
      typeValue = "";
    }
    const value = new URLSearchParams(location.search).get("value");
    console.log(value);
    console.log(
      `/api/search?value=${value}&type=${typeValue}&visited=${radioValue}`
    );
    let data = await fetch(
      `/api/search?value=${value}&type=${typeValue}&visited=${radioValue}`
    );
    console.log(data);
    adventureArray = [];
    let res = await data.json();
    adventureArray = res.adventures as Adventure[];
    console.log(radioValue);
  };
</script>

<main>
  <h1 class="text-center font-semibold text-2xl mb-2">Filtering Options</h1>
  <div class="flex items-center justify-center gap-6 mb-4">
    <div class="join">
      <input
        type="radio"
        name="visited"
        value="all"
        checked
        class="join-item btn"
        aria-label="All"
        bind:group={visitedValue}
      />
      <input
        type="radio"
        name="visited"
        value="false"
        class="join-item btn"
        bind:group={visitedValue}
        aria-label="Not Visited"
      />
      <input
        type="radio"
        name="visited"
        value="true"
        class="join-item btn"
        bind:group={visitedValue}
        aria-label="Visited"
      />
    </div>
    <br />
    <div class="join">
      <input
        type="radio"
        name="type"
        value=""
        class="join-item btn"
        bind:group={typeValue}
        aria-label="All"
      />
      <input
        type="radio"
        name="type"
        value="activity"
        class="join-item btn"
        bind:group={typeValue}
        aria-label="Activity"
      />
      <input
        type="radio"
        name="type"
        value="location"
        class="join-item btn"
        bind:group={typeValue}
        aria-label="Location"
      />
      <input
        type="radio"
        name="type"
        value="name"
        class="join-item btn"
        aria-label="Name"
        bind:group={typeValue}
      />
    </div>
    <button class="btn btn-primary" on:click={filterResults}>Filter</button>
  </div>

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
    <h1 class="text-center text-4xl font-bold mt-16">No Results Found</h1>
  {/if}
</main>
