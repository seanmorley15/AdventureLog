<script lang="ts">
  import type { Adventure } from "$lib/utils/types";
  import { createEventDispatcher } from "svelte";
  const dispatch = createEventDispatcher();
  import { onMount } from "svelte";
  let modal: HTMLDialogElement;

  export let adventure: Adventure;

  onMount(() => {
    modal = document.getElementById("my_modal_1") as HTMLDialogElement;
    if (modal) {
      modal.showModal();
    }
  });

  function close() {
    dispatch("close");
  }

  function viisted() {
    dispatch("visited");
    close();
  }
  function idea() {
    dispatch("idea");
    close();
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
    <h3 class="font-bold text-lg">
      Where should Adventure: {adventure.name} be added?
    </h3>
    <button class="btn btn-primary mr-2" on:click={viisted}
      >Visited Adventures</button
    >
    <button class="btn btn-primary" on:click={idea}>Adventure Idea</button>
    <button class="btn btn-neutral" on:click={close}>Close</button>
  </div>
</dialog>
