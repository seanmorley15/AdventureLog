<script lang="ts">
  export let data;
  import { goto } from "$app/navigation";
  import AdventureCard from "$lib/components/AdventureCard.svelte";
  import type { Adventure, Trip } from "$lib/utils/types.js";
  import AddFromFeatured from "$lib/components/AddLocationChooser.svelte";
  import { addAdventure } from "../../services/adventureService.js";
  import SucessToast from "$lib/components/SucessToast.svelte";

  let isShowingToast: boolean = false;
  let toastAction: string = "";

  let adventureToAdd: Adventure | null = null;

  function showToast(action: string) {
    toastAction = action;
    isShowingToast = true;

    setTimeout(() => {
      isShowingToast = false;
      toastAction = "";
    }, 3000);
  }

  async function add(event: CustomEvent<Adventure>) {
    adventureToAdd = event.detail;
  }

  const addToTrip = async (event: { detail: Trip }) => {
    if (!adventureToAdd) {
      showToast("Failed to add adventure");
      adventureToAdd = null;
    } else {
      let detailAdventure = adventureToAdd;
      detailAdventure.tripId = event.detail.id;
      detailAdventure.type = "planner";
      console.log(detailAdventure);
      let res = await fetch("/api/planner", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          detailAdventure,
        }),
      });
      if (res.status === 401) {
        goto("/login");
      } else {
        showToast("Adventure added to trip!");
        adventureToAdd = null;
      }
    }
  };

  async function addToVisted() {
    let detailAdventure = adventureToAdd;
    adventureToAdd = null;

    const response = await fetch("/api/visits", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        detailAdventure,
      }),
    });

    if (response.status === 401) {
      goto("/login");
    } else {
      showToast("Adventure added to visited list!");
    }
  }

  async function addIdea() {
    let detailAdventure = adventureToAdd;
    adventureToAdd = null;

    const response = await fetch("/api/planner", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        detailAdventure,
      }),
    });

    if (response.status === 401) {
      goto("/login");
    } else {
      showToast("Adventure added to idea list!");
    }
  }
</script>

{#if isShowingToast}
  <SucessToast action={toastAction} />
{/if}

{#if adventureToAdd}
  <AddFromFeatured
    adventure={adventureToAdd}
    on:close={() => (adventureToAdd = null)}
    on:visited={addToVisted}
    on:idea={addIdea}
    on:trip={addToTrip}
  />
{/if}

<div class="flex justify-center items-center w-full mt-4 mb-4">
  <article class="prose">
    <h1 class="text-center">Featured Adventure Locations</h1>
  </article>
</div>

<div
  class="grid xl:grid-cols-3 lg:grid-cols-3 md:grid-cols-2 sm:grid-cols-1 gap-4 mt-4 content-center auto-cols-auto ml-6 mr-6"
>
  {#each data.result as adventure (adventure.id)}
    <AdventureCard type="featured" on:add={add} {adventure} />
  {/each}
</div>

<svelte:head>
  <title>Featured Adventures | AdventureLog</title>
  <meta
    name="description"
    content="Featured Adventure Locations from around the world. Add them to your visited list!"
  />
</svelte:head>
