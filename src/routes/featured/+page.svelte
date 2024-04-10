<script lang="ts">
  export let data;
  console.log(data.result);
  import { goto } from "$app/navigation";
  import AdventureCard from "$lib/components/AdventureCard.svelte";
  import { visitCount } from "$lib/utils/stores/visitCountStore.js";
  import type { Adventure } from "$lib/utils/types.js";

  let count = 0;
  visitCount.subscribe((value) => {
    count = value;
  });

  async function add(event: CustomEvent<{ name: string; location: string }>) {
    const response = await fetch("/api/visits", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        name: event.detail.name,
        location: event.detail.location,
        created: "",
      }),
    });

    if (response.status === 401) {
      goto("/login");
    } else {
      visitCount.update((n) => n + 1);
    }
  }
</script>

<div class="flex justify-center items-center w-full mt-4 mb-4">
  <article class="prose">
    <h1 class="text-center">Featured Adventure Locations</h1>
  </article>
</div>

<div
  class="grid xl:grid-cols-3 lg:grid-cols-3 md:grid-cols-2 sm:grid-cols-1 gap-4 mt-4 content-center auto-cols-auto ml-6 mr-6"
>
  {#each data.result as adventure (adventure.id)}
    <AdventureCard
      type="featured"
      on:add={add}
      name={adventure.name}
      location={adventure.location}
      created=""
      id={NaN}
    />
  {/each}
</div>
