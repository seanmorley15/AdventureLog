<script lang="ts">
  import { createEventDispatcher } from "svelte";
  import locationDot from "$lib/assets/locationDot.svg";
  import calendar from "$lib/assets/calendar.svg";
  const dispatch = createEventDispatcher();

  export let type: String;

  export let name: String;
  export let location: String;
  export let created: string;
  export let id: Number;

  function remove() {
    dispatch("remove", id);
  }
  function edit() {
    dispatch("edit", id);
  }
  function add() {
    dispatch("add", { name, location });
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
