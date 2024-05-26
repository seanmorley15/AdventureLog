<script lang="ts">
  import type { Adventure, Trip } from "$lib/utils/types";
  import { createEventDispatcher } from "svelte";
  const dispatch = createEventDispatcher();
  import { onMount } from "svelte";
  let modal: HTMLDialogElement;

  let trips: Trip[] = [];

  export let adventure: Adventure;

  onMount(async () => {
    modal = document.getElementById("my_modal_1") as HTMLDialogElement;
    if (modal) {
      modal.showModal();
    }
    let res = await fetch("/api/trips");
    trips = await res.json();
    console.log(trips);
  });

  function close() {
    dispatch("close");
  }

  function visited() {
    dispatch("visited");
    close();
  }
  function idea() {
    dispatch("idea");
    close();
  }

  function trip(trip: Trip) {
    dispatch("trip", trip);
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
    <div class="flex items-center justify-center">
      <button class="btn btn-primary mr-2" on:click={visited}
        >Visited Adventures</button
      >
      <button class="btn btn-primary mr-2" on:click={idea}
        >Adventure Idea</button
      >
      <details class="dropdown">
        <summary class="m-1 btn">Add to Trip</summary>
        <ul
          class="p-2 shadow menu dropdown-content z-[1] bg-base-100 rounded-box w-52"
        >
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
        </ul>
      </details>
      <div class="h-32"></div>
      <button class="btn btn-neutral" on:click={close}>Close</button>
    </div>
  </div>
</dialog>
