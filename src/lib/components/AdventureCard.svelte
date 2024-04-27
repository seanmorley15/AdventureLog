<script lang="ts">
  import { createEventDispatcher } from "svelte";
  import locationDot from "$lib/assets/locationDot.svg";
  import calendar from "$lib/assets/calendar.svg";
  import { goto } from "$app/navigation";
  import { desc } from "drizzle-orm";
  const dispatch = createEventDispatcher();

  export let type: String;

  export let name: String | undefined = undefined;
  export let location: String | undefined = undefined;
  export let date: String | undefined = undefined;
  export let id: Number | undefined = undefined;
  export let regionId: String | undefined = undefined;
  export let visited: Boolean | undefined = undefined;

  function remove() {
    dispatch("remove", id);
  }
  function edit() {
    dispatch("edit", id);
  }
  function add() {
    dispatch("add", { name, location });
  }
  function markVisited() {
    dispatch("markVisited", regionId);
    visited = true;
  }
  function removeVisit() {
    dispatch("removeVisit", regionId);
    visited = false;
  }

  function moreInfo() {
    console.log(id);
    goto(`/adventure/${id}`);
  }
</script>

<div
  class="card min-w-max lg:w-96 md:w-80 sm:w-60 xs:w-40 bg-primary-content shadow-xl overflow-hidden text-base-content"
>
  <div class="card-body">
    <h2 class="card-title overflow-ellipsis">{name}</h2>
    {#if location && location !== ""}
      <div class="inline-flex items-center">
        <iconify-icon icon="mdi:map-marker" class="text-xl"></iconify-icon>
        <p class="ml-.5">{location}</p>
      </div>
    {/if}
    {#if date && date !== ""}
      <div class="inline-flex items-center">
        <iconify-icon icon="mdi:calendar" class="text-xl"></iconify-icon>
        <p class="ml-1">{date}</p>
      </div>
    {/if}
    <div class="card-actions justify-end">
      {#if type == "mylog"}
        <button class="btn btn-primary" on:click={edit}>Edit</button>
        <button class="btn btn-secondary" on:click={remove}>Remove</button>
        <button class="btn btn-primary" on:click={moreInfo}>Info</button>
      {/if}
      {#if type == "featured"}
        <button class="btn btn-primary" on:click={add}>Add</button>
      {/if}
    </div>
  </div>
</div>
