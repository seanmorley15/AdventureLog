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
    visitedValue = formData.get("visited") as string;
    typeValue = formData.get("type") as string;
    const value = new URLSearchParams(location.search).get("value");

    console.log(
      `/api/search?value=${value}&type=${typeValue}&visited=${visitedValue}`
    );

    let response = await fetch(
      `/api/search?value=${value}&type=${typeValue}&visited=${visitedValue}`
    );
    console.log(response);

    let res = await response.json();
    adventureArray = res.adventures as Adventure[];
    console.log("TEST" + visitedValue + " " + typeValue);
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
      checked={visitedValue === "all"}
    />
    All
    <input
      type="radio"
      bind:group={visitedValue}
      name="visited"
      value="false"
      class="radio radio-primary"
      checked={visitedValue === "false"}
    />
    Not Visited
    <input
      type="radio"
      bind:group={visitedValue}
      name="visited"
      value="true"
      class="radio radio-primary"
      checked={visitedValue === "true"}
    />
    Visited
    <br />
    <input
      type="radio"
      name="type"
      value=""
      class="radio radio-primary"
      bind:group={typeValue}
      checked={typeValue === ""}
    />
    All
    <input
      type="radio"
      name="type"
      value="activity"
      class="radio radio-primary"
      bind:group={typeValue}
      checked={typeValue === "activity"}
    />
    Activity
    <input
      type="radio"
      name="type"
      value="location"
      class="radio radio-primary"
      bind:group={typeValue}
      checked={typeValue === "location"}
    />
    Location
    <input
      type="radio"
      name="type"
      value="name"
      class="radio radio-primary"
      bind:group={typeValue}
      checked={typeValue === "name"}
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
