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
    console.log(adventure.activityTypes);
    dispatch("edit", adventure.id);
  }
  function add() {
    dispatch("add", adventure);
  }

  function moreInfo() {
    console.log(adventure.id);
    goto(`/adventure/${adventure.id}`);
  }
  function markVisited() {
    console.log(adventure.id);
    dispatch("markVisited", adventure);
  }
</script>

<div
  class="card min-w-max lg:w-96 md:w-80 sm:w-60 xs:w-40 bg-primary-content shadow-xl overflow-hidden text-base-content"
>
  {#if adventure.imageUrl && adventure.imageUrl.length > 0}
    <figure>
      <img
        src={adventure.imageUrl}
        alt="Shoes"
        class="w-full h-48 object-cover"
      />
    </figure>
  {/if}
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
    {#if adventure.activityTypes && adventure.activityTypes.length > 0}
      <ul class="flex flex-wrap">
        {#each adventure.activityTypes as activity}
          <div
            class="badge badge-primary mr-1 text-md font-semibold pb-2 pt-1 mb-1"
          >
            {activity}
          </div>
        {/each}
      </ul>
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
      {#if type == "planner"}
        <button class="btn btn-success" on:click={markVisited}
          ><iconify-icon icon="mdi:check-bold" class="text-2xl"
          ></iconify-icon></button
        >
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
      {#if type == "trip"}
        <!-- <button class="btn btn-primary" on:click={moreInfo}
          ><iconify-icon icon="mdi:launch" class="text-2xl"
          ></iconify-icon></button
        > -->
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
    </div>
  </div>
</div>
