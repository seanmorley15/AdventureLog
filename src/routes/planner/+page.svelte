<script lang="ts">
  import type { Adventure } from "$lib/utils/types.js";
  import { onMount } from "svelte";
  import AdventureCard from "$lib/components/AdventureCard.svelte";
  import EditModal from "$lib/components/EditModal.svelte";
  import MoreFieldsInput from "$lib/components/CreateNewAdventure.svelte";
  export let data;
  let plans: Adventure[] = [];
  let isLoading = true;

  onMount(async () => {
    console.log(data);
    plans = data.result;
    isLoading = false;
  });

  let isShowingMoreFields: boolean = false;

  let adventureToEdit: Adventure | undefined;

  console.log(data);

  function editPlan(event: { detail: number }) {
    const adventure = plans.find((adventure) => adventure.id === event.detail);
    if (adventure) {
      adventureToEdit = adventure;
    }
  }

  function handleClose() {
    adventureToEdit = undefined;
    isShowingMoreFields = false;
  }

  function savePlan(event: { detail: Adventure }) {
    console.log("Event", event.detail);
    let detailAdventure = event.detail;

    // put request to /api/visits with id and adventure data
    fetch("/api/planner", {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        detailAdventure,
      }),
    })
      .then((response) => response.json())
      .then((data) => {
        console.log("Success:", data);
        // update local array with new data
        const index = plans.findIndex(
          (adventure) => adventure.id === detailAdventure.id
        );
        if (index !== -1) {
          plans[index] = detailAdventure;
        }
        adventureToEdit = undefined;
        // showToast("Adventure edited successfully!");
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  }

  function removeAdventure(event: { detail: number }) {
    console.log("Event ID " + event.detail);
    // send delete request to server at /api/visits
    fetch("/api/visits", {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ id: event.detail }),
    })
      .then((response) => response.json())
      .then((data) => {
        console.log("Success:", data);
        // remove adventure from array where id matches
        plans = plans.filter((adventure) => adventure.id !== event.detail);
        // showToast("Adventure removed successfully!");
        // visitCount.update((n) => n - 1);
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  }

  const createNewAdventure = (event: { detail: Adventure }) => {
    isShowingMoreFields = false;
    let detailAdventure = event.detail;
    console.log("Event" + event.detail.name);

    fetch("/api/planner", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        detailAdventure,
      }),
    })
      .then((response) => {
        if (!response.ok) {
          return response.json().then((data) => {
            throw new Error(
              data.error || `Failed to add adventure - ${data?.message}`
            );
          });
        }
        return response.json();
      })
      .then((data) => {
        // add to local array for instant view update
        plans = [...plans, data.adventure];
        // showToast("Adventure added successfully!");
        // visitCount.update((n) => n + 1);
      })
      .catch((error) => {
        console.error("Error:", error);
        // showToast(error.message);
      });
  };
</script>

<div class="flex flex-row items-center justify-center gap-4">
  <button
    type="button"
    class="btn btn-secondary"
    on:click={() => (isShowingMoreFields = !isShowingMoreFields)}
  >
    <iconify-icon icon="mdi:plus" class="text-2xl"></iconify-icon>
  </button>
</div>

{#if isLoading}
  <div class="flex justify-center items-center w-full mt-16">
    <span class="loading loading-spinner w-24 h-24"></span>
  </div>
{/if}

<div
  class="grid xl:grid-cols-3 lg:grid-cols-3 md:grid-cols-2 sm:grid-cols-1 gap-4 mt-4 content-center auto-cols-auto ml-6 mr-6"
>
  {#each plans as adventure (adventure.id)}
    <AdventureCard
      {adventure}
      type="planner"
      on:edit={editPlan}
      on:remove={removeAdventure}
    />
  {/each}
</div>

{#if adventureToEdit && adventureToEdit.id != undefined}
  <EditModal bind:adventureToEdit on:submit={savePlan} on:close={handleClose} />
{/if}

{#if isShowingMoreFields}
  <MoreFieldsInput on:create={createNewAdventure} on:close={handleClose} />
{/if}
