<script lang="ts">
  import { enhance } from "$app/forms";
  import AdventureCard from "$lib/components/AdventureCard.svelte";
  import type { Adventure } from "$lib/utils/types";
  import type { SubmitFunction } from "@sveltejs/kit";
  import type { PageData } from "./$types";

  let visitedValue = "all";
  let typeValue = "";

  export let data: PageData;
  let adventureArray: Adventure[] = data.props?.adventures as Adventure[];

  const filter: SubmitFunction = async ({ formData }) => {
    const radioValue = formData.get("visited");
    const typeValue = formData.get("type");
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
  <form method="post" use:enhance={filter}>
    <input
      type="radio"
      name="visited"
      value="all"
      class="radio radio-primary"
      bind:group={visitedValue}
      checked
    />
    All
    <input
      type="radio"
      bind:group={visitedValue}
      name="visited"
      value="false"
      class="radio radio-primary"
    />
    Not Visited
    <input
      type="radio"
      bind:group={visitedValue}
      name="visited"
      value="true"
      class="radio radio-primary"
    />
    Visited
    <br />
    <input
      type="radio"
      name="type"
      value=""
      class="radio radio-primary"
      bind:group={typeValue}
    />
    All
    <input
      type="radio"
      name="type"
      value="activity"
      class="radio radio-primary"
      bind:group={typeValue}
    />
    Activity
    <input
      type="radio"
      name="type"
      bind:group={typeValue}
      value="location"
      class="radio radio-primary"
    />
    Location
    <input
      type="radio"
      bind:group={typeValue}
      name="type"
      value="name"
      class="radio radio-primary"
    />
    Name
    <!-- submit button -->
    <button type="submit" class="btn btn-primary">Search</button>
  </form>
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
