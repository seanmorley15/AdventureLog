<script lang="ts">
  import { createEventDispatcher } from "svelte";
  import locationDot from "$lib/assets/locationDot.svg";
  import calendar from "$lib/assets/calendar.svg";
  import { goto } from "$app/navigation";
  import { desc } from "drizzle-orm";
  import type { Adventure } from "$lib/utils/types";
  const dispatch = createEventDispatcher();

  export let type: String;

  export let adventure: Adventure;

  // export let name: String | undefined = undefined;
  // export let location: String | undefined = undefined;
  // export let date: String | undefined = undefined;
  // export let id: Number | undefined = undefined;

  function remove() {
    dispatch("remove", adventure.id);
  }
  function edit() {
    dispatch("edit", adventure.id);
  }
  function add() {
    dispatch("add", adventure);
  }

  function moreInfo() {
    console.log(adventure.id);
    goto(`/adventure/${adventure.id}`);
  }
</script>

<div
  class="card min-w-max lg:w-96 md:w-80 sm:w-60 xs:w-40 bg-primary-content shadow-xl overflow-hidden text-base-content"
>
  <div class="card-body">
    <h2 class="card-title overflow-ellipsis">{adventure.name}</h2>
    {#if adventure.location && adventure.location !== ""}
      <div class="inline-flex items-center">
        <iconify-icon icon="mdi:map-marker" class="text-xl"></iconify-icon>
        <p class="ml-.5">{adventure.location}</p>
      </div>
    {/if}
    {#if adventure.date && adventure.date !== ""}
      <div class="inline-flex items-center">
        <iconify-icon icon="mdi:calendar" class="text-xl"></iconify-icon>
        <p class="ml-1">{adventure.date}</p>
      </div>
    {/if}
    <div class="card-actions justify-end">
      {#if type == "mylog"}
        <button class="btn btn-primary" on:click={moreInfo}
          ><iconify-icon icon="mdi:launch" class="text-2xl"
          ></iconify-icon></button
        >
        <button class="btn btn-primary" on:click={edit}
          ><iconify-icon icon="mdi:file-document-edit" class="text-2xl"
          ></iconify-icon></button
        >
        <button class="btn btn-secondary" on:click={remove}
          ><iconify-icon icon="mdi:trash-can-outline" class="text-2xl"
          ></iconify-icon></button
        >
      {/if}
      {#if type == "featured"}
        <button class="btn btn-primary" on:click={add}
          ><iconify-icon icon="mdi:plus" class="text-2xl"
          ></iconify-icon></button
        >
      {/if}
    </div>
  </div>
</div>
