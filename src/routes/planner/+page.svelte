<script lang="ts">
  import type { Adventure } from "$lib/utils/types.js";
  import { onMount } from "svelte";
  import AdventureCard from "$lib/components/AdventureCard.svelte";
  import EditModal from "$lib/components/EditModal.svelte";
  import MoreFieldsInput from "$lib/components/CreateNewAdventure.svelte";
  import {
    saveAdventure,
    removeAdventure,
    addAdventure,
    changeType,
  } from "../../services/adventureService.js";
  import SucessToast from "$lib/components/SucessToast.svelte";
  import mapDrawing from "$lib/assets/adventure_map.svg";
  export let data;
  let plans: Adventure[] = [];
  let isLoading = true;

  onMount(async () => {
    console.log(data);
    plans = data.result;
    isLoading = false;
  });

  let isShowingMoreFields: boolean = false;

  let isShowingToast: boolean = false;
  let toastAction: string = "";

  let adventureToEdit: Adventure | undefined;

  console.log(data);

  function showToast(action: string) {
    toastAction = action;
    isShowingToast = true;

    setTimeout(() => {
      isShowingToast = false;
      toastAction = "";
    }, 3000);
  }

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

  async function savePlan(event: { detail: Adventure }) {
    let newArray = await saveAdventure(event.detail, plans);
    if (newArray.length > 0) {
      plans = newArray;
      showToast("Adventure updated successfully!");
    } else {
      showToast("Failed to update adventure");
    }
    adventureToEdit = undefined;
  }

  async function remove(event: { detail: number }) {
    let initialLength: number = plans.length;
    let theAdventure = plans.find((adventure) => adventure.id === event.detail);
    if (theAdventure) {
      let newArray = await removeAdventure(theAdventure, plans);
      if (newArray.length === initialLength - 1) {
        plans = newArray;
        showToast("Adventure removed successfully!");
      } else {
        showToast("Failed to remove adventure");
      }
    }
  }

  const createNewAdventure = async (event: { detail: Adventure }) => {
    isShowingMoreFields = false;
    let newArray = await addAdventure(event.detail, plans);
    if (newArray.length > 0) {
      plans = newArray;
      showToast("Adventure added successfully!");
    } else {
      showToast("Failed to add adventure");
    }
  };

  async function markVisited(event: { detail: Adventure }) {
    let initialLength: number = plans.length;
    let newArray = await changeType(event.detail, "mylog", plans);
    if (newArray.length + 1 == initialLength) {
      plans = newArray;
      showToast("Adventure moved to visit log!");
    } else {
      showToast("Failed to moves adventure");
    }
    adventureToEdit = undefined;
  }
</script>

{#if isShowingToast}
  <SucessToast action={toastAction} />
{/if}

<div class="flex justify-center items-center w-full mt-4 mb-4">
  <article class="prose">
    <h2 class="text-center">Add new Plan</h2>
  </article>
</div>

<div class="flex flex-row items-center justify-center gap-4">
  <button
    type="button"
    class="btn btn-secondary"
    on:click={() => (isShowingMoreFields = !isShowingMoreFields)}
  >
    <iconify-icon icon="mdi:plus" class="text-2xl"></iconify-icon>
  </button>
</div>
{#if plans.length != 0}
  <div class="flex justify-center items-center w-full mt-4 mb-4">
    <article class="prose">
      <h1 class="text-center">My Adventure Plans</h1>
    </article>
  </div>
{/if}

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
      on:remove={remove}
      on:markVisited={markVisited}
    />
  {/each}
</div>

{#if plans.length == 0 && !isLoading}
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

<!-- ----------------------- -->

<!-- {#if plans.length == 0 && !isLoading}
  <div class="flex flex-col items-center justify-center mt-16">
    <article class="prose mb-4"><h2>Add some adventures!</h2></article>
    <img src={mapDrawing} width="25%" alt="Logo" />
  </div>
{/if}

{#if plans.length != 0 && !isLoading}
  <div class="flex justify-center items-center w-full mt-4">
    <article class="prose">
      <h2 class="text-center">Actions</h2>
    </article>
  </div>
  <div
    class="flex flex-row items-center justify-center mt-2 gap-4 mb-4 flex-wrap"
  >
    <button class="btn btn-neutral" on:click={exportData}>
      <img src={exportFile} class="inline-block -mt-1" alt="Logo" /> Save as File
    </button>
    <button class="btn btn-neutral" on:click={() => (confirmModalOpen = true)}>
      <img src={deleteIcon} class="inline-block -mt-1" alt="Logo" /> Delete Data
    </button>
    <button class="btn btn-neutral" on:click={shareLink}>
      <iconify-icon icon="mdi:share-variant" class="text-xl"></iconify-icon> Share
      as Link
    </button>
  </div>
{/if}

{#if confirmModalOpen}
  <ConfirmModal
    on:close={handleClose}
    on:confirm={deleteData}
    title="Delete all Adventures"
    isWarning={false}
    message="Are you sure you want to delete all adventures?"
  />
{/if} -->

<svelte:head>
  <title>My Plans | AdventureLog</title>
  <meta
    name="description"
    content="Create and manage your adventure plans here!"
  />
</svelte:head>
