<script lang="ts">
  import { goto } from "$app/navigation";
  import { createEventDispatcher } from "svelte";
  const dispatch = createEventDispatcher();

  export let regionId: String | undefined = undefined;
  export let countryCode: String | undefined = undefined;
  export let visited: Boolean | undefined = undefined;
  export let name: String | undefined = undefined;

  function markVisited() {
    dispatch("markVisited", regionId);
    visited = true;
  }
  function removeVisit() {
    dispatch("removeVisit", regionId);
    visited = false;
  }
  function moreInfo() {
    goto(`/worldtravel/${countryCode}/${regionId}`);
  }
</script>

<div
  class="card min-w-max lg:w-96 md:w-80 sm:w-60 xs:w-40 bg-primary-content shadow-xl overflow-hidden text-base-content"
>
  <div class="card-body">
    <h2 class="card-title overflow-ellipsis">{name}</h2>
    <p>{regionId}</p>
    <div class="card-actions justify-end">
      <!-- <button class="btn btn-info" on:click={moreInfo}>More Info</button> -->
      {#if !visited}
        <button class="btn btn-primary" on:click={markVisited}
          >Mark Visited</button
        >
      {/if}
      {#if visited}
        <button class="btn btn-warning" on:click={removeVisit}>Remove</button>
      {/if}
    </div>
  </div>
</div>
