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
  {#if adventure.name}
    <h1 class="text-center font-extrabold text-4xl mb-2">{adventure.name}</h1>
  {/if}
  {#if adventure.location}
    <p class="text-center text-2xl">
      <iconify-icon icon="mdi:map-marker" class="text-xl -mb-0.5"
      ></iconify-icon>{adventure.location}
    </p>
  {/if}
  {#if adventure.date}
    <p class="text-center text-lg mt-4 pl-16 pr-16">
      Visited on: {new Date(adventure.date).toLocaleDateString()}
    </p>
  {/if}
  {#if adventure.rating !== undefined && adventure.rating !== null}
    <div class="flex justify-center items-center">
      <div class="rating" aria-readonly="true">
        {#each Array.from({ length: 5 }, (_, i) => i + 1) as star}
          <input
            type="radio"
            name="rating-1"
            class="mask mask-star"
            checked={star <= adventure.rating}
            disabled
          />
        {/each}
      </div>
    </div>
  {/if}
  {#if adventure.description}
    <p class="text-center text-lg mt-4 pl-16 pr-16">{adventure.description}</p>
  {/if}
  {#if adventure.imageUrl}
    <div class="flex content-center justify-center">
      <img
        src={adventure.imageUrl}
        alt={adventure.name}
        class="w-50 mt-4 align-middle rounded-lg shadow-lg"
      />
    </div>
  {/if}
{/if}
