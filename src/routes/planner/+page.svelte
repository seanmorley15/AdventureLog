<script lang="ts">
  import type { Adventure, Trip } from "$lib/utils/types";
  import { onMount } from "svelte";
  import AdventureCard from "$lib/components/AdventureCard.svelte";
  import EditModal from "$lib/components/EditModal.svelte";
  import MoreFieldsInput from "$lib/components/CreateNewAdventure.svelte";
  import {
    saveAdventure,
    removeAdventure,
    addAdventure,
    changeType,
  } from "../../services/adventureService";
  import SucessToast from "$lib/components/SucessToast.svelte";
  import mapDrawing from "$lib/assets/adventure_map.svg";
  import CreateNewTripPlan from "$lib/components/CreateNewTripPlan.svelte";
  import TripCard from "$lib/components/TripCard.svelte";
  export let data;

  let adventuresPlans: Adventure[] = [];
  let tripPlans: Trip[] = [];

  let activityTypes: String[] = [];

  let isLoadingIdeas: boolean = true;
  let isLoadingTrips: boolean = true;

  onMount(async () => {
    getAllTrips();
    adventuresPlans = data.result;
    isLoadingIdeas = false;
    activityTypes = data.activityTypesResult.types;
  });

  let isShowingMoreFields: boolean = false;
  let isShowingNewTrip: boolean = false;

  let isShowingToast: boolean = false;
  let toastAction: string = "";

  let adventureToEdit: Adventure | undefined;

  function showToast(action: string) {
    toastAction = action;
    isShowingToast = true;

    setTimeout(() => {
      isShowingToast = false;
      toastAction = "";
    }, 3000);
  }

  function editPlan(event: { detail: number }) {
    const adventure = adventuresPlans.find(
      (adventure) => adventure.id === event.detail
    );
    if (adventure) {
      adventureToEdit = adventure;
    }
  }

  function handleClose() {
    adventureToEdit = undefined;
    isShowingMoreFields = false;
  }

  async function savePlan(event: { detail: Adventure }) {
    let types: String[] = [];
    if (event.detail.activityTypes && event.detail.activityTypes.length > 0) {
      types = event.detail.activityTypes;
    }
    let newArray = await saveAdventure(event.detail, adventuresPlans);
    if (newArray.length > 0) {
      adventuresPlans = newArray;
      showToast("Adventure updated successfully!");
      activityTypes = activityTypes.concat(types);
      activityTypes = [...new Set(activityTypes)];
    } else {
      showToast("Failed to update adventure");
    }
    adventureToEdit = undefined;
  }

  async function remove(event: { detail: number }) {
    let initialLength: number = adventuresPlans.length;
    let theAdventure = adventuresPlans.find(
      (adventure) => adventure.id === event.detail
    );
    if (theAdventure) {
      let newArray = await removeAdventure(theAdventure, adventuresPlans);
      if (newArray.length === initialLength - 1) {
        adventuresPlans = newArray;
        showToast("Adventure removed successfully!");
      } else {
        showToast("Failed to remove adventure");
      }
    }
  }

  const createNewAdventure = async (event: { detail: Adventure }) => {
    isShowingMoreFields = false;
    let types: String[] = [];
    if (event.detail.activityTypes && event.detail.activityTypes.length > 0) {
      types = event.detail.activityTypes;
    }
    let newArray = await addAdventure(event.detail, adventuresPlans);
    if (newArray.length > 0) {
      adventuresPlans = newArray;
      showToast("Adventure added successfully!");
      activityTypes = activityTypes.concat(types);
      activityTypes = [...new Set(activityTypes)];
    } else {
      showToast("Failed to add adventure");
    }
  };

  async function markVisited(event: { detail: Adventure }) {
    let initialLength: number = adventuresPlans.length;
    let newArray = await changeType(event.detail, "mylog", adventuresPlans);
    if (newArray.length + 1 == initialLength) {
      adventuresPlans = newArray;
      showToast("Adventure moved to visit log!");
    } else {
      showToast("Failed to moves adventure");
    }
    adventureToEdit = undefined;
  }

  async function createNewTrip(event: { detail: Trip }) {
    isShowingNewTrip = false;
    let newTrip: Trip = event.detail;
    // post the trip object to /api/trips
    // if successful, add the trip to the tripPlans array
    const response = await fetch("/api/trips", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ newTrip }),
    })
      .then((response) => response.json())
      .then((data) => {
        console.log("Success:", data);
        newTrip = data.trip;
        console.log(newTrip);
        tripPlans = [...tripPlans, newTrip];
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  }

  async function getAllTrips() {
    const response = await fetch("/api/trips", {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    })
      .then((response) => response.json())
      .then((data) => {
        console.log("Success:", data);
        tripPlans = data;
        isLoadingTrips = false;
      })
      .catch((error) => {
        showToast("Failed to get trips");
      });
  }

  async function removeTrip(event: { detail: number }) {
    let initialLength: number = tripPlans.length;
    const response = await fetch("/api/trips", {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ id: event.detail }),
    })
      .then((response) => response.json())
      .then((data) => {
        console.log("Success:", data);
        let theTrip = tripPlans.find((trip) => trip.id === event.detail);
        if (theTrip) {
          let newArray = tripPlans.filter((trip) => trip.id !== event.detail);
          if (newArray.length === initialLength - 1) {
            tripPlans = newArray;
            showToast("Trip removed successfully!");
          } else {
            showToast("Failed to remove trip");
          }
        }
      })
      .catch((error) => {
        showToast("Failed to get trips");
      });
  }
</script>

{#if isShowingToast}
  <SucessToast action={toastAction} />
{/if}

<div class="fixed bottom-4 right-4 z-[999]">
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
          on:click={() => (isShowingMoreFields = true)}>Adventure Idea</button
        >
        <button
          class="btn btn-primary"
          on:click={() => (isShowingNewTrip = true)}>Trip Planner</button
        >
      </ul>
    </div>
  </div>
</div>

{#if adventuresPlans.length != 0}
  <div class="flex justify-center items-center w-full mt-4 mb-4">
    <article class="prose">
      <h1 class="text-center">My Adventure Ideas</h1>
    </article>
  </div>
  <div class="flex justify-center items-center w-full mt-4 mb-4">
    Activity Type &nbsp;
    <select class="select select-bordered w-full max-w-xs">
      <option value="">All</option>
      {#each activityTypes as type}
        <option value={type}>{type}</option>
      {/each}
    </select>
  </div>
{/if}

{#if isLoadingIdeas && isLoadingTrips}
  <div class="flex justify-center items-center w-full mt-16">
    <span class="loading loading-spinner w-24 h-24"></span>
  </div>
{/if}

<div class="flex flex-wrap gap-4 mr-4 ml-4 justify-center content-center">
  {#each adventuresPlans as adventure (adventure.id)}
    <AdventureCard
      {adventure}
      type="planner"
      on:edit={editPlan}
      on:remove={remove}
      on:markVisited={markVisited}
    />
  {/each}
</div>

{#if adventuresPlans.length == 0 && !isLoadingIdeas && !isLoadingTrips && !isShowingMoreFields && !isShowingNewTrip && tripPlans.length > 0}
  <div class="flex flex-col items-center justify-center mt-16">
    <article class="prose mb-4"><h2>Add some plans!</h2></article>
    <img src={mapDrawing} width="25%" alt="Logo" />
  </div>
{/if}

{#if adventureToEdit && adventureToEdit.id != undefined}
  <EditModal bind:adventureToEdit on:submit={savePlan} on:close={handleClose} />
{/if}

{#if isShowingMoreFields}
  <MoreFieldsInput
    on:create={createNewAdventure}
    on:close={handleClose}
    type="planner"
  />
{/if}

{#if isShowingNewTrip}
  <CreateNewTripPlan
    on:close={() => (isShowingNewTrip = false)}
    on:create={createNewTrip}
  />
{/if}

{#if tripPlans.length !== 0}
  <div class="flex justify-center items-center w-full mt-4 mb-4">
    <article class="prose">
      <h1 class="text-center">My Trip Ideas</h1>
    </article>
  </div>
{/if}

<div
  class="grid xl:grid-cols-3 lg:grid-cols-3 md:grid-cols-2 sm:grid-cols-1 gap-4 mt-4 content-center auto-cols-auto ml-6 mr-6"
>
  {#each tripPlans as trip (trip.id)}
    <TripCard {trip} on:remove={removeTrip} />
  {/each}
</div>

{#if tripPlans.length == 0 && !isLoadingIdeas && !isLoadingTrips && !isShowingMoreFields && !isShowingNewTrip && adventuresPlans.length > 0}
  <div class="flex flex-col items-center justify-center mt-16">
    <article class="prose mb-4"><h2>Add some trips!</h2></article>
    <img src={mapDrawing} width="25%" alt="Logo" />
  </div>
{/if}

{#if tripPlans.length == 0 && !isLoadingIdeas && !isLoadingTrips && !isShowingMoreFields && !isShowingNewTrip && adventuresPlans.length == 0}
  <div class="flex flex-col items-center justify-center mt-16">
    <article class="prose mb-4"><h2>Add some trips and plans!</h2></article>
    <img src={mapDrawing} width="25%" alt="Logo" />
  </div>
{/if}

<svelte:head>
  <title>My Plans | AdventureLog</title>
  <meta
    name="description"
    content="Create and manage your adventure plans here!"
  />
</svelte:head>
