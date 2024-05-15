<script lang="ts">
  import type { Adventure, Trip } from "$lib/utils/types";
  import { onMount } from "svelte";
  import type { PageData } from "./$types";
  import { goto } from "$app/navigation";
  import CreateNewAdventure from "$lib/components/CreateNewAdventure.svelte";
  import {
    addAdventure,
    saveAdventure,
  } from "../../../services/adventureService";
  import AdventureCard from "$lib/components/AdventureCard.svelte";
  import EditModal from "$lib/components/EditModal.svelte";
  import SucessToast from "$lib/components/SucessToast.svelte";

  export let data: PageData;

  let trip: Trip;

  let isCreateModalOpen: boolean = false;

  let adventuresPlans: Adventure[] = [];
  let adventureToEdit: Adventure | undefined;

  onMount(() => {
    if (data.trip.trip) {
      trip = data.trip.trip[0];
      adventuresPlans = data.trip.adventures;
      console.log(adventuresPlans);
    } else {
      goto("/404");
    }
  });

  function handleClose() {
    adventureToEdit = undefined;
    isCreateModalOpen = false;
  }

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

  let isShowingToast: boolean = false;
  let toastAction: string = "";

  function showToast(action: string) {
    toastAction = action;
    isShowingToast = true;

    setTimeout(() => {
      isShowingToast = false;
      toastAction = "";
    }, 3000);
  }

  async function savePlan(event: { detail: Adventure }) {
    let newArray = await saveAdventure(event.detail, adventuresPlans);
    if (newArray.length > 0) {
      adventuresPlans = newArray;
      showToast("Adventure updated successfully!");
    } else {
      showToast("Failed to update adventure");
    }
    adventureToEdit = undefined;
  }

  function edit(event: { detail: number }) {
    const adventure = adventuresPlans.find(
      (adventure) => adventure.id === event.detail
    );
    if (adventure) {
      adventureToEdit = adventure;
    }
  }
</script>

{#if isShowingToast}
  <SucessToast action={toastAction} />
{/if}

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
    <AdventureCard {adventure} type="trip" on:edit={edit} />
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

{#if adventureToEdit && adventureToEdit.id != undefined}
  <EditModal bind:adventureToEdit on:submit={savePlan} on:close={handleClose} />
{/if}
