<script lang="ts">
  export let data;
  let adventures: Adventure[] = [];
  let isLoading = true;

  import AdventureCard from "$lib/components/AdventureCard.svelte";
  import type { Adventure } from "$lib/utils/types";
  import { onMount } from "svelte";
  import exportFile from "$lib/assets/exportFile.svg";
  import ConfirmModal from "$lib/components/ConfirmModal.svelte";
  import deleteIcon from "$lib/assets/deleteIcon.svg";
  import SucessToast from "$lib/components/SucessToast.svelte";
  import mapDrawing from "$lib/assets/adventure_map.svg";
  import EditModal from "$lib/components/EditModal.svelte";
  import { generateRandomString } from "$lib";
  import { visitCount } from "$lib/utils/stores/visitCountStore";
  import MoreFieldsInput from "$lib/components/CreateNewAdventure.svelte";
  import {
    addAdventure,
    removeAdventure,
    saveAdventure,
  } from "../../services/adventureService.js";

  let isShowingMoreFields = false;

  let adventureToEdit: Adventure | undefined;

  let isShowingToast: boolean = false;
  let toastAction: string = "";
  let confirmModalOpen: boolean = false;

  // Sets the adventures array to the data from the server
  onMount(async () => {
    console.log(data);
    adventures = data.result;
    isLoading = false;
  });

  let count = 0;
  visitCount.subscribe((value) => {
    count = value;
  });

  function showToast(action: string) {
    toastAction = action;
    isShowingToast = true;

    setTimeout(() => {
      isShowingToast = false;
      toastAction = "";
    }, 3000);
  }

  function exportData() {
    let jsonString = JSON.stringify(adventures);
    let blob = new Blob([jsonString], { type: "application/json" });
    let url = URL.createObjectURL(blob);

    let link = document.createElement("a");
    link.download = "adventurelog-export.json";
    link.href = url;
    link.click();
    URL.revokeObjectURL(url);
  }

  const createNewAdventure = async (event: { detail: Adventure }) => {
    isShowingMoreFields = false;
    let newArray = await addAdventure(event.detail, adventures);
    if (newArray.length > 0) {
      adventures = newArray;
      showToast("Adventure added successfully!");
    } else {
      showToast("Failed to add adventure");
    }
  };

  async function save(event: { detail: Adventure }) {
    let newArray = await saveAdventure(event.detail, adventures);
    if (newArray.length > 0) {
      adventures = newArray;
      showToast("Adventure updated successfully!");
    } else {
      showToast("Failed to update adventure");
    }
    adventureToEdit = undefined;
  }

  function editAdventure(event: { detail: number }) {
    const adventure = adventures.find(
      (adventure) => adventure.id === event.detail
    );
    if (adventure) {
      adventureToEdit = adventure;
    }
  }

  function shareLink() {
    let key = generateRandomString();

    // console log each adventure in the array
    for (let i = 0; i < adventures.length; i++) {
      console.log(adventures[i]);
    }

    let data = JSON.stringify(adventures);
    fetch("/api/share", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ key, data }),
    })
      .then((response) => response.json())
      .then((data) => {
        console.log("Success:", data);
        let url = window.location.origin + "/shared/" + key;
        navigator.clipboard.writeText(url);
        showToast("Link copied to clipboard!");
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  }

  function handleClose() {
    adventureToEdit = undefined;
    confirmModalOpen = false;
    isShowingMoreFields = false;
  }

  function deleteData() {
    fetch("/api/clearvisits", {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
      },
    })
      .then((response) => response.json())
      .then((data) => {
        console.log("Success:", data);
        // remove adventure from array where id matches
        adventures = [];
        showToast("Adventure removed successfully!");
        visitCount.set(0);
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  }

  async function remove(event: { detail: number }) {
    let initialLength: number = adventures.length;
    let theAdventure = adventures.find(
      (adventure) => adventure.id === event.detail
    );
    if (theAdventure) {
      let newArray = await removeAdventure(theAdventure, adventures);
      if (newArray.length === initialLength - 1) {
        adventures = newArray;
        showToast("Adventure removed successfully!");
      } else {
        showToast("Failed to remove adventure");
      }
    }
  }
</script>

<div class="flex justify-center items-center w-full mt-4 mb-4">
  <article class="prose">
    <h2 class="text-center">Add new Location</h2>
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
{#if adventures.length != 0}
  <div class="flex justify-center items-center w-full mt-4 mb-4">
    <article class="prose">
      <h1 class="text-center">My Visited Adventure Locations</h1>
    </article>
  </div>
{/if}

{#if isLoading}
  <div class="flex justify-center items-center w-full mt-16">
    <span class="loading loading-spinner w-24 h-24"></span>
  </div>
{/if}

{#if isShowingToast}
  <SucessToast action={toastAction} />
{/if}

{#if isShowingMoreFields}
  <MoreFieldsInput
    on:create={createNewAdventure}
    on:close={handleClose}
    type="mylog"
  />
{/if}

{#if adventureToEdit && adventureToEdit.id != undefined}
  <EditModal bind:adventureToEdit on:submit={save} on:close={handleClose} />
{/if}

<div
  class="grid xl:grid-cols-3 lg:grid-cols-3 md:grid-cols-2 sm:grid-cols-1 gap-4 mt-4 content-center auto-cols-auto ml-6 mr-6"
>
  {#each adventures as adventure (adventure.id)}
    <AdventureCard
      {adventure}
      type="mylog"
      on:edit={editAdventure}
      on:remove={remove}
    />
  {/each}
</div>

{#if adventures.length == 0 && !isLoading}
  <div class="flex flex-col items-center justify-center mt-16">
    <article class="prose mb-4"><h2>Add some adventures!</h2></article>
    <img src={mapDrawing} width="25%" alt="Logo" />
  </div>
{/if}

{#if adventures.length != 0 && !isLoading}
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
{/if}

<svelte:head>
  <title>My Log | AdventureLog</title>
  <meta
    name="description"
    content="Displays the user's visited adventure locations."
  />
</svelte:head>
