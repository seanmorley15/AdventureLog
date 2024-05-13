<script lang="ts">
  import { createEventDispatcher } from "svelte";
  import locationDot from "$lib/assets/locationDot.svg";
  import calendar from "$lib/assets/calendar.svg";
  import { goto } from "$app/navigation";
  import { desc } from "drizzle-orm";
  import type { Adventure, Trip } from "$lib/utils/types";
  const dispatch = createEventDispatcher();

  //   export let type: String;

  export let trip: Trip;

  function remove() {
    dispatch("remove", trip.id);
  }
  function edit() {}
  function add() {
    dispatch("add", trip);
  }

  function moreInfo() {
    console.log(trip.id);
    goto(`/trip/${trip.id}`);
  }

  function markVisited() {
    console.log(trip.id);
    dispatch("markVisited", trip);
  }
</script>

<div
  class="card min-w-max lg:w-96 md:w-80 sm:w-60 xs:w-40 bg-primary-content shadow-xl overflow-hidden text-base-content"
>
  <div class="card-body">
    <h2 class="card-title overflow-ellipsis">{trip.name}</h2>
    {#if trip.description && trip.description !== ""}
      <div class="inline-flex items-center">
        <iconify-icon icon="mdi:map-marker" class="text-xl"></iconify-icon>
        <p class="ml-.5">{trip.description}</p>
      </div>
    {/if}
    {#if trip.startDate && trip.startDate !== ""}
      <div class="inline-flex items-center">
        <iconify-icon icon="mdi:calendar" class="text-xl"></iconify-icon>
        <p class="ml-1">{trip.startDate}</p>
      </div>
    {/if}
    {#if trip.endDate && trip.endDate !== ""}
      <div class="inline-flex items-center">
        <iconify-icon icon="mdi:calendar" class="text-xl"></iconify-icon>
        <p class="ml-1">{trip.endDate}</p>
      </div>
    {/if}
    <div class="card-actions justify-end">
      <button class="btn btn-secondary" on:click={remove}
        ><iconify-icon icon="mdi:trash-can-outline" class="text-2xl"
        ></iconify-icon></button
      >
    </div>
  </div>
</div>
