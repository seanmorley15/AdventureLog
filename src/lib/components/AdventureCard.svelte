<script lang="ts">
  import { createEventDispatcher } from "svelte";
  import locationDot from "$lib/assets/locationDot.svg";
  import calendar from "$lib/assets/calendar.svg";
  import { goto } from "$app/navigation";
  const dispatch = createEventDispatcher();

  export let type: String;

  export let name: String | undefined = undefined;
  export let location: String | undefined = undefined;
  export let created: String | undefined = undefined;
  export let id: Number | undefined = undefined;
  export let regionId: String | undefined = undefined;
  export let visited: Boolean | undefined = undefined;
  export let countryCode: String | undefined = undefined;

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
    goto(`/worldtravel/${countryCode}/${regionId}`);
  }
</script>

{#if type === "mylog"}
  <div
    class="card min-w-max lg:w-96 md:w-80 sm:w-60 xs:w-40 bg-neutral shadow-xl overflow-hidden"
  >
    <div class="card-body">
      <h2 class="card-title overflow-ellipsis">{name}</h2>
      {#if location !== ""}
        <p>
          <img
            src={locationDot}
            class="inline-block -mt-1 mr-1"
            alt="Logo"
          />{location}
        </p>
      {/if}
      {#if created !== ""}
        <p>
          <img
            src={calendar}
            class="inline-block -mt-1 mr-1"
            alt="Logo"
          />{created}
        </p>
      {/if}
      <div class="card-actions justify-end">
        <button class="btn btn-primary" on:click={edit}>Edit</button>
        <button class="btn btn-secondary" on:click={remove}>Remove</button>
      </div>
    </div>
  </div>
{/if}

{#if type === "featured"}
  <div
    class="card min-w-max lg:w-96 md:w-80 sm:w-60 xs:w-40 bg-neutral shadow-xl overflow-hidden"
  >
    <div class="card-body">
      <h2 class="card-title overflow-ellipsis">{name}</h2>
      {#if location != ""}
        <p>
          <img
            src={locationDot}
            class="inline-block -mt-1 mr-1"
            alt="Logo"
          />{location}
        </p>
      {/if}
      <div class="card-actions justify-end">
        <button class="btn btn-primary" on:click={add}>Add</button>
      </div>
    </div>
  </div>
{/if}

{#if type === "shared"}
  <div
    class="card min-w-max lg:w-96 md:w-80 sm:w-60 xs:w-40 bg-neutral shadow-xl overflow-hidden"
  >
    <div class="card-body">
      <h2 class="card-title overflow-ellipsis">{name}</h2>
      {#if location !== ""}
        <p>
          <img
            src={locationDot}
            class="inline-block -mt-1 mr-1"
            alt="Logo"
          />{location}
        </p>
      {/if}
      {#if created !== ""}
        <p>
          <img
            src={calendar}
            class="inline-block -mt-1 mr-1"
            alt="Logo"
          />{created}
        </p>
      {/if}
    </div>
  </div>
{/if}

{#if type === "worldtravelregion"}
  <div
    class="card min-w-max lg:w-96 md:w-80 sm:w-60 xs:w-40 bg-neutral shadow-xl overflow-hidden"
  >
    <div class="card-body">
      <h2 class="card-title overflow-ellipsis">{name}</h2>
      <p>{regionId}</p>
      <div class="card-actions justify-end">
        <button class="btn btn-info" on:click={moreInfo}>More Info</button>
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
{/if}
