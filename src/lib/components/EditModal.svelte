<script lang="ts">
  export let adventureToEdit: Adventure;
  import { createEventDispatcher } from "svelte";
  import type { Adventure } from "$lib/utils/types";
  const dispatch = createEventDispatcher();
  import { onMount } from "svelte";
  let modal: HTMLDialogElement;

  console.log(adventureToEdit.id);

  let originalName = adventureToEdit.name;

  onMount(() => {
    modal = document.getElementById("my_modal_1") as HTMLDialogElement;
    if (modal) {
      modal.showModal();
    }
    activityInput = (adventureToEdit?.activityTypes || []).join(", ");
  });

  function submit() {
    addActivityType();
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

  function addActivityType() {
    if (activityInput.trim() !== "") {
      const activities = activityInput
        .split(",")
        .filter((activity) => activity.trim() !== "");
      adventureToEdit.activityTypes = activities;
      activityInput = "";
    }
    console.log(adventureToEdit.activityTypes);
  }
</script>

<dialog id="my_modal_1" class="modal">
  <!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
  <!-- svelte-ignore a11y-no-noninteractive-tabindex -->
  <div class="modal-box" role="dialog" on:keydown={handleKeydown} tabindex="0">
    <h3 class="font-bold text-lg">Edit Adventure {originalName}</h3>
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
            bind:value={adventureToEdit.name}
            class="input input-bordered w-full max-w-xs"
          />
        </div>
        <div>
          <label for="location">Location</label>
          <input
            type="text"
            id="location"
            bind:value={adventureToEdit.location}
            class="input input-bordered w-full max-w-xs"
          />
        </div>
        <div>
          <label for="date">Date</label>
          <input
            type="date"
            id="date"
            bind:value={adventureToEdit.date}
            class="input input-bordered w-full max-w-xs"
          />
        </div>
        <div>
          <label for="date">Description</label>
          <input
            type="text"
            id="description"
            bind:value={adventureToEdit.description}
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
        </div>
        <div>
          <label for="rating">Rating</label>
          <input
            type="number"
            min="0"
            max="5"
            id="rating"
            bind:value={adventureToEdit.rating}
            class="input input-bordered w-full max-w-xs"
          />
        </div>
        <button class="btn btn-primary mr-4 mt-4" on:click={submit}>Save</button
        >
        <!-- if there is a button in form, it will close the modal -->
        <button class="btn mt-4" on:click={close}>Close</button>
      </form>
    </div>
  </div>
</dialog>
