<script lang="ts">
  export let adventureToEdit: Adventure;
  import { createEventDispatcher } from "svelte";
  import type { Adventure } from "$lib/utils/types";
  const dispatch = createEventDispatcher();
  import { onMount } from "svelte";
  import { addActivityType, generateDescription, getImage } from "$lib";
  import AutoComplete from "./AutoComplete.svelte";
  import ImageModal from "./ImageModal.svelte";
  let modal: HTMLDialogElement;

  console.log(adventureToEdit.id);

  let originalName = adventureToEdit.name;

  let activityTypes: string[] = [];

  $: selected = "";

  // on selection add to activityTypes
  $: {
    if (selected) {
      adventureToEdit = addActivityType(selected, adventureToEdit);

      if (activityInput.length === 0) {
        activityInput = selected;
      } else {
        activityInput = activityInput + ", " + selected;
      }
      selected = "";
    }
  }

  onMount(async () => {
    modal = document.getElementById("my_modal_1") as HTMLDialogElement;
    if (modal) {
      modal.showModal();
    }
    activityInput = (adventureToEdit?.activityTypes || []).join(", ");
    let activityFetch = await fetch(
      "/api/activitytypes?type=" + adventureToEdit.type
    );
    let res = await activityFetch.json();
    activityTypes = res.types;
  });

  function submit() {
    activitySetup();
    dispatch("submit", adventureToEdit);
    console.log(adventureToEdit);
  }

  function close() {
    dispatch("close");
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === "Escape") {
      close();
    }
  }

  let activityInput: string = "";

  function activitySetup() {
    adventureToEdit = addActivityType(activityInput, adventureToEdit);
    activityInput = "";
  }

  async function generate() {
    try {
      console.log(adventureToEdit.name);
      const desc = await generateDescription(adventureToEdit.name);
      adventureToEdit.description = desc;
      // Do something with the updated adventureToEdit object
    } catch (error) {
      console.error(error);
      // Handle the error
    }
  }

  async function searchImage() {
    try {
      const imageUrl = await getImage(adventureToEdit.name);
      adventureToEdit.imageUrl = imageUrl;
    } catch (error) {
      console.error(error);
      // Handle the error
    }
  }

  let isImageModalOpen: boolean = false;

  /**
   * Handles the upload event and updates the adventure's image URL.
   *
   * @param {CustomEvent<any>} e - The custom event containing the key.
   */
  function upload(e: CustomEvent<any>) {
    let key = e.detail;
    console.log("EE" + key);
    adventureToEdit.imageUrl = key;
  }
</script>

{#if isImageModalOpen}
  <ImageModal
    name={adventureToEdit.name}
    on:submit={upload}
    on:close={() => (isImageModalOpen = false)}
    existingImageKey={adventureToEdit.imageUrl}
    bucket="adventures"
  />
{/if}

<dialog id="my_modal_1" class="modal">
  <!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
  <!-- svelte-ignore a11y-no-noninteractive-tabindex -->
  <div class="modal-box" role="dialog" on:keydown={handleKeydown} tabindex="0">
    <h3 class="font-bold text-lg">Edit Adventure: {adventureToEdit.name}</h3>
    <div
      class="modal-action items-center"
      style="display: flex; flex-direction: column; align-items: center; width: 100%;"
    >
      <form method="dialog" style="width: 100%;">
        <div class="mb-2">
          <label for="name">Name</label><br />
          <input
            type="text"
            id="name"
            bind:value={adventureToEdit.name}
            class="input input-bordered w-full max-w-xs mt-1"
          />
        </div>
        <div class="mb-2">
          <label for="location"
            >Location<iconify-icon
              icon="mdi:map-marker"
              class="text-lg ml-0.5 -mb-0.5"
            ></iconify-icon></label
          ><br />
          <input
            type="text"
            id="location"
            bind:value={adventureToEdit.location}
            class="input input-bordered w-full max-w-xs mt-1"
          />
        </div>
        <div class="mb-2">
          <label for="date"
            >Date<iconify-icon icon="mdi:calendar" class="text-lg ml-1 -mb-0.5"
            ></iconify-icon></label
          ><br />
          <input
            type="date"
            id="date"
            bind:value={adventureToEdit.date}
            class="input input-bordered w-full max-w-xs mt-1"
          />
        </div>
        <div class="mb-2">
          <label for="date"
            >Description<iconify-icon
              icon="mdi:notebook"
              class="text-lg ml-1 -mb-0.5"
            ></iconify-icon></label
          ><br />
          <div class="flex">
            <input
              type="text"
              id="description"
              bind:value={adventureToEdit.description}
              class="input input-bordered w-full max-w-xs mt-1 mb-2"
            />
            <button
              class="btn btn-neutral ml-2"
              type="button"
              on:click={generate}
              ><iconify-icon icon="mdi:wikipedia" class="text-xl -mb-1"
              ></iconify-icon>Generate Description</button
            >
          </div>
        </div>
        <div class="mb-2">
          <label for="activityTypes"
            >Activity Types <iconify-icon
              icon="mdi:clipboard-list"
              class="text-xl -mb-1"
            ></iconify-icon></label
          ><br />
          <input
            type="text"
            hidden
            id="activityTypes"
            bind:value={activityInput}
            class="input input-bordered w-full max-w-xs mt-1"
          />

          <AutoComplete
            items={activityTypes}
            bind:selectedItem={selected}
            bind:displayValue={activityInput}
          />
        </div>
        <div class="mb-2">
          <label for="rating"
            >Rating <iconify-icon icon="mdi:star" class="text-xl -mb-1"
            ></iconify-icon></label
          ><br />
          <input
            type="number"
            min="0"
            max="5"
            id="rating"
            bind:value={adventureToEdit.rating}
            class="input input-bordered w-full max-w-xs mt-1"
          />
        </div>
        <div>
          <button
            type="button"
            class="btn btn-neutral"
            on:click={() => {
              isImageModalOpen = true;
            }}
          >
            <iconify-icon icon="mdi:upload" class="text-xl"
            ></iconify-icon>Upload Image
          </button>
        </div>

        <button
          type="submit"
          class="btn btn-primary mr-4 mt-4"
          on:click={submit}>Create</button
        >
        <!-- if there is a button in form, it will close the modal -->
        <button class="btn mt-4" on:click={close}>Close</button>
      </form>
      <div class="flex items-center justify-center flex-wrap gap-4 mt-4"></div>
    </div>
  </div>
</dialog>
