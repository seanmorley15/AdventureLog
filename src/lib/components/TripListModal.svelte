<script lang="ts">
  import { onMount } from "svelte";
  import type { Trip } from "$lib/utils/types";
  import { createEventDispatcher } from "svelte";
  const dispatch = createEventDispatcher();
  let modal: HTMLDialogElement;
  let trips: Trip[] = [];

  onMount(async () => {
    modal = document.getElementById("my_modal_1") as HTMLDialogElement;
    if (modal) {
      modal.showModal();
    }
    let res = await fetch("/api/trips");
    trips = await res.json();
    console.log(trips);
  });

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === "Escape") {
      close();
    }
  }

  function close() {
    dispatch("close");
  }
</script>

<dialog id="my_modal_1" class="modal">
  <!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
  <!-- svelte-ignore a11y-no-noninteractive-tabindex -->
  <div class="modal-box" role="dialog" on:keydown={handleKeydown} tabindex="0">
    <h3 class="font-bold text-lg">Choose a trip</h3>
    {#each trips as trip}
      <li>
        <button
          class="btn btn-primary"
          on:click={() => {
            dispatch("trip", trip);
            close();
          }}
        >
          {trip.name}
        </button>
      </li>
    {/each}
    {#if trips.length === 0}
      <p>No trips found</p>
    {/if}
  </div>
  <!-- close button -->
  <button class="btn btn-neutral" on:click={close}>Close</button>
</dialog>
