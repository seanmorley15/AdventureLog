<script lang="ts">
  import { enhance } from "$app/forms";
  import type { PageData } from "./$types";

  export let data: PageData;
  import { goto } from "$app/navigation";
  import campingDrawing from "$lib/assets/camping.svg";
  import { visitCount } from "$lib/utils/stores/visitCountStore";

  async function navToLog() {
    goto("/log");
  }
</script>

<div class="flex flex-col items-center justify-center">
  {#if data.user && data.user.username != ""}
    <h1 class="mb-6 text-4xl font-extrabold">
      Welcome {data.user.first_name}. Let's get Exploring!
    </h1>
  {:else}
    <h1 class="mb-6 text-4xl font-extrabold">Welcome. Let's get Exploring!</h1>
  {/if}

  <img src={campingDrawing} class="w-1/4 mb-4" alt="Logo" />
  <button on:click={navToLog} class="btn btn-primary mb-4">Open Log</button>

  <div class="stats shadow">
    <div class="stat">
      <div class="stat-title">Logged Adventures</div>
      <div class="stat-value text-center">{$visitCount}</div>
      <!-- <div class="stat-desc">21% more than last month</div> -->
    </div>
  </div>
</div>

<svelte:head>
  <title>Home | AdventureLog</title>
  <meta
    name="description"
    content="AdventureLog is a platform to log your adventures."
  />
</svelte:head>
