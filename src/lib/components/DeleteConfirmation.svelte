<script lang="ts">
  import { createEventDispatcher } from "svelte";
  import type { Adventure } from "$lib/utils/types";
  const dispatch = createEventDispatcher();
  import { onMount } from "svelte";
  let modal: HTMLDialogElement;

  onMount(() => {
    modal = document.getElementById("my_modal_1") as HTMLDialogElement;
    if (modal) {
      modal.showModal();
    }
  });

  function close() {
    dispatch("close");
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === "Escape") {
      close();
    }
  }
</script>

<dialog id="my_modal_1" class="modal">
  <!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
  <!-- svelte-ignore a11y-no-noninteractive-tabindex -->
  <div class="modal-box" role="dialog" on:keydown={handleKeydown} tabindex="0">
    <h3 class="font-bold text-lg">Edit Adventure</h3>
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
            class="input input-bordered w-full max-w-xs"
          />
        </div>
        <div>
          <label for="location">Location</label>
          <input
            type="text"
            id="location"
            class="input input-bordered w-full max-w-xs"
          />
        </div>
        <div>
          <label for="date">date</label>
          <input
            type="date"
            id="date"
            class="input input-bordered w-full max-w-xs"
          />
        </div>
        <!-- <button class="btn btn-primary mr-4 mt-4" on:click={submit}>Save</button
        > -->
        <!-- if there is a button in form, it will close the modal -->
        <button class="btn mt-4" on:click={close}>Close</button>
      </form>
    </div>
  </div>
</dialog>
