<script lang="ts">
  import type { Adventure, Trip } from "$lib/utils/types";
  import { createEventDispatcher } from "svelte";
  const dispatch = createEventDispatcher();
  import { onMount } from "svelte";
  import TripListModal from "./TripListModal.svelte";
  let modal: HTMLDialogElement;

  export let adventure: Adventure;

  let tripModal: boolean = false;

  onMount(async () => {
    modal = document.getElementById("my_modal_1") as HTMLDialogElement;
    if (modal) {
      modal.showModal();
    }
  });

  function close() {
    dispatch("close");
  }

  function openTripModal() {
    tripModal = true;
  }

  function visited() {
    dispatch("visited");
    close();
  }
  function idea() {
    dispatch("idea");
    close();
  }

  function trip(event: CustomEvent<any>) {
    dispatch("trip", event.detail);
    close();
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === "Escape") {
      close();
    }
  }
</script>

{#if tripModal}
  <TripListModal on:close={close} on:trip={trip} />
{/if}

<dialog id="my_modal_1" class="modal">
  <!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
  <!-- svelte-ignore a11y-no-noninteractive-tabindex -->
  <div class="modal-box" role="dialog" on:keydown={handleKeydown} tabindex="0">
    <h3 class="font-bold text-lg">
      Where should Adventure: {adventure.name} be added?
    </h3>
    <div class="flex items-center justify-center">
      <button class="btn btn-primary mr-2" on:click={visited}
        >Visited Adventures</button
      >
      <button class="btn btn-primary mr-2" on:click={idea}
        >Adventure Idea</button
      >
      <button class="btn btn-primary mr-2" on:click={openTripModal}
        >Add to Trip</button
      >
      <div class="h-32"></div>
      <button class="btn btn-neutral" on:click={close}>Close</button>
    </div>
  </div>
</dialog>
