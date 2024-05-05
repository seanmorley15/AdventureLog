<script lang="ts">
  import { enhance } from "$app/forms";
  import type { PageData } from "./$types";

  export let data: PageData;
  import { goto } from "$app/navigation";
  import campingDrawing from "$lib/assets/camping.svg";
  import { visitCount } from "$lib/utils/stores/visitCountStore";
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

<section class="w-full py-12 md:py-24 lg:py-32">
  <div class="container px-4 md:px-6">
    <div
      class="grid gap-6 lg:grid-cols-[1fr_550px] lg:gap-12 xl:grid-cols-[1fr_650px]"
    >
      <div class="flex flex-col justify-center space-y-4">
        <div class="space-y-2">
          <h1
            class="text-3xl font-bold tracking-tighter sm:text-5xl xl:text-6xl/none"
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
<section class="w-full py-12 md:py-24 lg:py-32 bg-gray-100 dark:bg-gray-800">
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
          class="text-3xl font-bold tracking-tighter sm:text-5xl dark:text-gray-400"
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

<!-- <section class="w-full py-12 md:py-24 lg:py-32 border-t">
  <div
    class="container grid items-center justify-center gap-4 px-4 text-center md:px-6"
  >
    <div class="space-y-3">
      <h2 class="text-3xl font-bold tracking-tighter md:text-4xl/tight">
        Explore the World's Most Breathtaking Destinations
      </h2>
      <p
        class="mx-auto max-w-[600px] text-gray-500 md:text-xl/relaxed lg:text-base/relaxed xl:text-xl/relaxed dark:text-gray-400"
      >
        F
      </p>
    </div>
    <div
      aria-roledescription="carousel"
      class="relative w-full max-w-5xl"
      role="region"
    >
      <div class="overflow-hidden">
        <div class="flex -ml-4" style="transform: translate3d(0px, 0px, 0px);">
          <div
            aria-roledescription="slide"
            class="min-w-0 shrink-0 grow-0 basis-full pl-4 md:basis-1/2 lg:basis-1/3"
            role="group"
          >
            <div class="p-1">
              <div
                class="rounded-lg border bg-card text-card-foreground shadow-sm"
                data-v0-t="card"
              >
                <img
                  src="/placeholder.svg"
                  width="400"
                  height="300"
                  alt="Destination"
                  class="aspect-[4/3] overflow-hidden rounded-t-xl object-cover"
                />
                <div class="space-y-2 p-4">
                  <h3 class="text-xl font-bold">Machu Pic</h3>
                  <p class="text-gray-500 dark:text-gray-400"></p>
                </div>
              </div>
            </div>
          </div>
          <div
            aria-roledescription="slide"
            class="min-w-0 shrink-0 grow-0 basis-full pl-4 md:basis-1/2 lg:basis-1/3"
            role="group"
          >
            <div class="p-1">
              <div
                class="rounded-lg border bg-card text-card-foreground shadow-sm"
                data-v0-t="card"
              >
                <img
                  src="/placeholder.svg"
                  width="400"
                  height="300"
                  alt="Destination"
                  class="aspect-[4/3] overflow-hidden rounded-t-xl object-cover"
                />
                <div class="space-y-2 p-4">
                  <h3 class="text-xl font-bold">Patagonia, Argentina</h3>
                  <p class="text-gray-500 dark:text-gray-400"></p>
                </div>
              </div>
            </div>
          </div>
          <div
            aria-roledescription="slide"
            class="min-w-0 shrink-0 grow-0 basis-full pl-4 md:basis-1/2 lg:basis-1/3"
            role="group"
          >
            <div class="p-1">
              <div
                class="rounded-lg border bg-card text-card-foreground shadow-sm"
                data-v0-t="card"
              >
                <img
                  src="/placeholder.svg"
                  width="400"
                  height="300"
                  alt="Destination"
                  class="aspect-[4/3] overflow-hidden rounded-t-xl object-cover"
                />
                <div class="space-y-2 p-4">
                  <h3 class="text-xl font-bold">Bali, Indonesia</h3>
                  <p class="text-gray-500 dark:text-gray-400">
                    Discover lush jungles, stunning beaches, and ancient
                    temples.
                  </p>
                </div>
              </div>
            </div>
          </div>
          <div
            aria-roledescription="slide"
            class="min-w-0 shrink-0 grow-0 basis-full pl-4 md:basis-1/2 lg:basis-1/3"
            role="group"
          >
            <div class="p-1">
              <div
                class="rounded-lg border bg-card text-card-foreground shadow-sm"
                data-v0-t="card"
              >
                <img
                  src="/placeholder.svg"
                  width="400"
                  height="300"
                  alt="Destination"
                  class="aspect-[4/3] overflow-hidden rounded-t-xl object-cover"
                />
                <div class="space-y-2 p-4">
                  <h3 class="text-xl font-bold">Banff, Canada</h3>
                  <p class="text-gray-500 dark:text-gray-400"></p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <button
        class="inline-flex items-center justify-center whitespace-nowrap text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground absolute h-8 w-8 rounded-full -left-12 top-1/2 -translate-y-1/2"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          class="h-4 w-4"
        >
          <path d="m12 19-7-7 7-7"></path>
          <path d="M19 12H5"></path>
        </svg>
        <span class="sr-only">Previous slide</span>
      </button>
      <button
        class="inline-flex items-center justify-center whitespace-nowrap text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground absolute h-8 w-8 rounded-full -right-12 top-1/2 -translate-y-1/2"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          class="h-4 w-4"
        >
          <path d="M5 12h14"></path>
          <path d="m12 5 7 7-7 7"></path>
        </svg>
        <span class="sr-only">Next slide</span>
      </button>
    </div>
  </div>
</section> -->

<svelte:head>
  <title>Home | AdventureLog</title>
  <meta
    name="description"
    content="AdventureLog is a platform to log your adventures."
  />
</svelte:head>
