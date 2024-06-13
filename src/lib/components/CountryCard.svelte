<script lang="ts">
  import { goto } from "$app/navigation";
  import { getFlag } from "$lib";
  import { createEventDispatcher } from "svelte";
  const dispatch = createEventDispatcher();

  export let countryName: string | undefined = undefined;
  export let countryCode: string;

  async function nav() {
    goto(`/worldtravel/${countryCode}`);
  }
</script>

<div
  class="card w-full max-w-xs sm:max-w-sm md:max-w-md lg:max-w-md xl:max-w-md bg-primary-content shadow-xl overflow-hidden text-base-content"
>
  <figure>
    <!-- svelte-ignore a11y-img-redundant-alt -->
    <img
      src={getFlag(240, countryCode) ||
        "https://placehold.co/300?text=No%20Image%20Found&font=roboto"}
      alt="No image available"
      class="w-full h-48 object-cover"
    />
  </figure>
  <div class="card-body">
    <h2 class="card-title overflow-ellipsis">{countryName}</h2>
    <div class="card-actions justify-end">
      <!-- <button class="btn btn-info" on:click={moreInfo}>More Info</button> -->
      <button class="btn btn-primary" on:click={nav}>Open</button>
    </div>
  </div>
</div>
