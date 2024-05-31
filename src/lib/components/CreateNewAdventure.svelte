<script lang="ts">
  let newAdventure: Adventure;
  export let type: string;

  newAdventure = {
    id: -1,
    type: type,
    name: "",
    location: "",
    date: "",
    activityTypes: [],
    imageUrl: "",
  };

  import { createEventDispatcher } from "svelte";
  import type { Adventure } from "$lib/utils/types";
  const dispatch = createEventDispatcher();
  import { onMount } from "svelte";
  import { addActivityType, generateDescription, getImage } from "$lib";
  import AutoComplete from "./AutoComplete.svelte";
  let modal: HTMLDialogElement;

  let activityTypes: string[] = [];

  $: selected = "";

  // on selection add to activityTypes
  $: {
    if (selected) {
      newAdventure = addActivityType(selected, newAdventure);

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
    let activityFetch = await fetch("/api/activitytypes?type=" + type);
    let res = await activityFetch.json();
    activityTypes = res.types;
  });

  function create() {
    activitySetup();
    if (newAdventure.name.trim() === "") {
      alert("Name is required");
      return;
    }
    dispatch("create", newAdventure);
    console.log(newAdventure);
  }

  function close() {
    dispatch("close");
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === "Escape") {
      close();
    }
  }

  async function generate() {
    try {
      console.log(newAdventure.name);
      const desc = await generateDescription(newAdventure.name);
      newAdventure.description = desc;
      // Do something with the updated newAdventure object
    } catch (error) {
      console.error(error);
      // Handle the error
    }
  }

  async function searchImage() {
    try {
      const imageUrl = await getImage(newAdventure.name);
      newAdventure.imageUrl = imageUrl;
    } catch (error) {
      console.error(error);
      // Handle the error
    }
  }

  let activityInput: string = "";

  function activitySetup() {
    newAdventure = addActivityType(activityInput, newAdventure);
    activityInput = "";
  }
</script>

<dialog id="my_modal_1" class="modal">
  <!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
  <!-- svelte-ignore a11y-no-noninteractive-tabindex -->
  <div class="modal-box" role="dialog" on:keydown={handleKeydown} tabindex="0">
    <h3 class="font-bold text-lg">New Adventure</h3>
    <p class="py-4">Press ESC key or click the button below to close</p>
    <div
      class="modal-action items-center"
      style="display: flex; flex-direction: column; align-items: center; width: 100%;"
    >
      <form method="dialog" style="width: 100%;">
        <div>
          <label for="name">Name</label>
          <input
            type="text"
            id="name"
            required
            bind:value={newAdventure.name}
            class="input input-bordered w-full max-w-xs"
          />
        </div>
        <div>
          <label for="location">Location</label>
          <input
            type="text"
            id="location"
            bind:value={newAdventure.location}
            class="input input-bordered w-full max-w-xs"
          />
        </div>
        <div>
          <label for="date">date</label>
          <input
            type="date"
            id="date"
            bind:value={newAdventure.date}
            class="input input-bordered w-full max-w-xs"
          />
        </div>
        <div>
          <label for="date">Description</label>
          <input
            type="text"
            id="description"
            bind:value={newAdventure.description}
            class="input input-bordered w-full max-w-xs"
          />
        </div>

        <div>
          <label for="date">Activity Types (Comma Seperated)</label>
          <input
            type="text"
            id="activityTypes"
            bind:value={activityInput}
            class="input input-bordered w-full max-w-xs"
          />
          <AutoComplete items={activityTypes} bind:selectedItem={selected} />
        </div>
        <div>
          <label for="rating">Rating</label>
          <input
            type="number"
            min="0"
            max="5"
            id="rating"
            bind:value={newAdventure.rating}
            class="input input-bordered w-full max-w-xs"
          />
        </div>
        <div>
          <label for="rating">Image URL</label>
          <input
            type="url"
            id="iamgeUrl"
            bind:value={newAdventure.imageUrl}
            class="input input-bordered w-full max-w-xs"
          />
        </div>

        <button
          type="submit"
          class="btn btn-primary mr-4 mt-4"
          on:click={create}>Create</button
        >
        <!-- if there is a button in form, it will close the modal -->
        <button class="btn mt-4" on:click={close}>Close</button>
      </form>
      <div class="flex items-center justify-center flex-wrap gap-4 mt-4">
        <button class="btn btn-secondary" on:click={generate}
          >Generate Description</button
        >
        <button class="btn btn-secondary" on:click={searchImage}
          >Search for Image</button
        >
      </div>
    </div>
  </div>
</dialog>
