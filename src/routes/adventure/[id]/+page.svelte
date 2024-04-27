<script lang="ts">
  import type { Adventure } from "$lib/utils/types";
  import { onMount } from "svelte";
  import type { PageData } from "./$types";
  import { goto } from "$app/navigation";

  export let data: PageData;

  let adventure: Adventure;

  onMount(() => {
    if (data.adventure.adventure) {
      adventure = data.adventure.adventure[0];
    } else {
      goto("/404");
    }
  });
</script>

{#if !adventure}
  <div class="flex justify-center items-center w-full mt-16">
    <span class="loading loading-spinner w-24 h-24"></span>
  </div>
{:else}
  <h1 class="text-center font-extrabold text-4xl">{adventure.name}</h1>
  <p>{adventure.location}</p>
{/if}
