<script lang="ts">
  import { enhance } from "$app/forms";
  import type { PageData } from "./$types";

  export let data: PageData;
  import { goto } from "$app/navigation";
  import campingDrawing from "$lib/assets/camping.svg";
  import AdventureOverlook from "$lib/assets/AdventureOverlook.webp";
  import MapWithPins from "$lib/assets/MapWithPins.webp";

  async function navToLog() {
    goto("/log");
  }
</script>

<!--
// v0 by Vercel.
// https://v0.dev/t/PyTNahbwxVP
-->

<section
  class="flex items-center justify-center w-full py-12 md:py-24 lg:py-32"
>
  <div class="container px-4 md:px-6">
    <div
      class="grid gap-6 lg:grid-cols-[1fr_550px] lg:gap-12 xl:grid-cols-[1fr_650px]"
    >
      <div class="flex flex-col justify-center space-y-4">
        <div class="space-y-2">
          <h1
            class="text-3xl font-bold tracking-tighter sm:text-5xl xl:text-6xl/none bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent pb-4"
          >
            Discover the World's Most Thrilling Adventures
          </h1>
          <p class="max-w-[600px] text-gray-500 md:text-xl dark:text-gray-400">
            Discover and plan your next epic adventure with our cutting-edge
            travel app. Explore breathtaking destinations, create custom
            itineraries, and stay connected on the go.
          </p>
        </div>
        <div class="flex flex-col gap-2 min-[400px]:flex-row">
          <button
            on:click={() => goto("/log")}
            class="inline-flex h-10 items-center justify-center rounded-md bg-gray-900 px-8 text-sm font-medium text-gray-50 shadow transition-colors hover:bg-gray-900/90 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-gray-950 disabled:pointer-events-none disabled:opacity-50 dark:bg-gray-50 dark:text-gray-900 dark:hover:bg-gray-50/90 dark:focus-visible:ring-gray-300"
          >
            Go To AdventureLog
          </button>
        </div>
      </div>
      <img
        src={AdventureOverlook}
        width="550"
        height="550"
        alt="Hero"
        class="mx-auto aspect-video overflow-hidden rounded-xl object-cover sm:w-full lg:order-last"
      />
    </div>
  </div>
</section>
<section
  class="flex items-center justify-center w-full py-12 md:py-24 lg:py-32 bg-gray-100 dark:bg-gray-800"
>
  <div class="container px-4 md:px-6">
    <div
      class="flex flex-col items-center justify-center space-y-4 text-center"
    >
      <div class="space-y-2">
        <div
          class="inline-block rounded-lg bg-gray-100 px-3 py-1 text-md dark:bg-gray-800 dark:text-gray-400"
        >
          Key Features
        </div>
        <h2
          class="text-3xl font-bold tracking-tighter sm:text-5xl bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent"
        >
          Discover, Plan, and Explore with Ease
        </h2>
        <p
          class="max-w-[900px] text-gray-500 md:text-xl/relaxed lg:text-base/relaxed xl:text-xl/relaxed dark:text-gray-400"
        >
          Our adventure travel app is designed to simplify your journey,
          providing you with the tools and resources to plan, pack, and navigate
          your next epic adventure.
        </p>
      </div>
    </div>
    <div
      class="mx-auto grid max-w-5xl items-center gap-6 py-12 lg:grid-cols-2 lg:gap-12"
    >
      <!-- svelte-ignore a11y-img-redundant-alt -->
      <img
        src={MapWithPins}
        width="550"
        height="310"
        alt="Image"
        class="mx-auto aspect-video overflow-hidden rounded-xl object-cover object-center sm:w-full lg:order-last"
      />
      <div class="flex flex-col justify-center space-y-4">
        <ul class="grid gap-6">
          <li>
            <div class="grid gap-1">
              <h3 class="text-xl font-bold dark:text-gray-400">
                Trip Planning
              </h3>
              <p class="text-gray-500 dark:text-gray-400">
                Easily create custom itineraries and get real-time updates on
                your trip.
              </p>
            </div>
          </li>
          <li>
            <div class="grid gap-1">
              <h3 class="text-xl font-bold dark:text-gray-400">
                Packing Lists
              </h3>
              <p class="text-gray-500 dark:text-gray-400">
                Never forget a thing with our comprehensive packing lists.
              </p>
            </div>
          </li>
          <li>
            <div class="grid gap-1">
              <h3 class="text-xl font-bold dark:text-gray-400">
                Destination Guides
              </h3>
              <p class="text-gray-500 dark:text-gray-400">
                Discover the best attractions, activities, and hidden gems in
                your destination.
              </p>
            </div>
          </li>
        </ul>
      </div>
    </div>
  </div>
</section>

<svelte:head>
  <title>Home | AdventureLog</title>
  <meta
    name="description"
    content="AdventureLog is a platform to log your adventures."
  />
</svelte:head>
