<script lang="ts">
  import { goto } from "$app/navigation";
  import campingDrawing from "$lib/assets/camping.svg";
  import { visitCount } from "$lib/utils/stores/visitCountStore";

  async function navToLog() {
    goto("/log");
  }
</script>

<div class="flex flex-col items-center justify-center">
  <article class="prose">
    <h1 class="mb-4">Welcome. Let's get Exploring!</h1>
  </article>
  <img src={campingDrawing} class="w-1/4 mb-4" alt="Logo" />
  <button on:click={navToLog} class="btn btn-primary">Open Log</button>

  <div class="stats shadow">
    <div class="stat">
      <div class="stat-title">Logged Adventures</div>
      <div class="stat-value text-center">{$visitCount}</div>
      <!-- <div class="stat-desc">21% more than last month</div> -->
    </div>
  </div>
</div>
