<script lang="ts">
  import type { Adventure, Trip } from "$lib/utils/types";
  import { onMount } from "svelte";
  import type { PageData } from "./$types";
  import { goto } from "$app/navigation";
  import CreateNewAdventure from "$lib/components/CreateNewAdventure.svelte";
  import { addAdventure } from "../../../services/adventureService";
  import AdventureCard from "$lib/components/AdventureCard.svelte";

  export let data: PageData;

  let trip: Trip;

  let isCreateModalOpen: boolean = false;

  let adventuresPlans: Adventure[] = [];

  onMount(() => {
    if (data.trip.trip) {
      trip = data.trip.trip[0];
      adventuresPlans = data.trip.adventures;
      console.log(adventuresPlans);
    } else {
      goto("/404");
    }
  });

  const newAdventure = async (event: { detail: Adventure }) => {
    isCreateModalOpen = false;
    let detailAdventure = event.detail;
    detailAdventure.tripId = trip.id;
    let newArray = await addAdventure(detailAdventure, adventuresPlans);
    if (newArray.length > 0) {
      adventuresPlans = newArray;
      // showToast("Adventure added successfully!");
    } else {
      // showToast("Failed to add adventure");
    }
  };
</script>

<main>
  {#if trip && trip.name}
    <h1 class="text-center font-extrabold text-4xl mb-2">{trip.name}</h1>
  {/if}
  {#if trip && trip.description}
    <p class="text-center text-lg mt-4 pl-16 pr-16">{trip.description}</p>
  {/if}
  {#if trip && trip.startDate}
    <p class="text-center text-lg mt-4 pl-16 pr-16">
      Start Date: {trip.startDate}
    </p>
  {/if}
  {#if trip && trip.endDate}
    <p class="text-center text-lg mt-4 pl-16 pr-16">End Date: {trip.endDate}</p>
  {/if}
</main>

<div
  class="grid xl:grid-cols-3 lg:grid-cols-3 md:grid-cols-2 sm:grid-cols-1 gap-4 mt-4 content-center auto-cols-auto ml-6 mr-6"
>
  {#each adventuresPlans as adventure (adventure.id)}
    <AdventureCard {adventure} type="trip" />
  {/each}
</div>

<div class="fixed bottom-4 right-4">
  <div class="flex flex-row items-center justify-center gap-4">
    <div class="dropdown dropdown-top dropdown-end">
      <div tabindex="0" role="button" class="btn m-1 size-16 btn-primary">
        <iconify-icon icon="mdi:plus" class="text-2xl"></iconify-icon>
      </div>
      <!-- svelte-ignore a11y-no-noninteractive-tabindex -->
      <ul
        tabindex="0"
        class="dropdown-content z-[1] menu p-4 shadow bg-base-300 text-base-content rounded-box w-52 gap-4"
      >
        <p class="text-center font-bold text-lg">Create new...</p>
        <button
          class="btn btn-primary"
          on:click={() => (isCreateModalOpen = true)}>Adventure</button
        >
        <!-- <button
          class="btn btn-primary"
          on:click={() => (isShowingNewTrip = true)}>Trip Planner</button
        > -->
      </ul>
    </div>
  </div>
</div>

{#if isCreateModalOpen}
  <CreateNewAdventure
    type="planner"
    on:close={() => {
      isCreateModalOpen = false;
    }}
    on:create={newAdventure}
  />
{/if}
