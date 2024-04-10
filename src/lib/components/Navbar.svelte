<script lang="ts">
  import { enhance } from "$app/forms";
  import { visitCount } from "$lib/utils/stores/visitCountStore";
  import { goto } from "$app/navigation";
  import type { DatabaseUser } from "$lib/server/auth";
  export let user: any;
  import UserAvatar from "./UserAvatar.svelte";
  import { onMount } from "svelte";
  async function goHome() {
    goto("/");
  }
  async function goToLog() {
    goto("/log");
  }
  async function goToFeatured() {
    goto("/featured");
  }
  async function toToLogin() {
    goto("/login");
  }
  async function toToSignup() {
    goto("/signup");
  }

  let count = 0;

  // get value from fetch /api/visitcount

  onMount(async () => {
    const res = await fetch("/api/visitcount");
    const data = await res.json();
    visitCount.set(data.visitCount);
  });

  visitCount.subscribe((value) => {
    count = value;
  });

  // Set the visit count to the number of adventures stored in local storage
  const isBrowser = typeof window !== "undefined";
  if (isBrowser) {
    const storedAdventures = localStorage.getItem("adventures");
  }
</script>

<div class="navbar bg-base-100 flex flex-col md:flex-row">
  <div class="navbar-start flex justify-around md:justify-start">
    <button
      class="btn btn-primary my-2 md:my-0 md:mr-4 md:ml-2"
      on:click={goHome}>Home</button
    >
    {#if user}
      <button
        class="btn btn-primary my-2 md:my-0 md:mr-4 md:ml-2"
        on:click={goToLog}>My Log</button
      >
    {/if}
    <button class="btn btn-primary my-2 md:my-0" on:click={goToFeatured}
      >Featured</button
    >
  </div>
  <div class="navbar-center flex justify-center md:justify-center">
    <a class="btn btn-ghost text-xl" href="/">AdventureLog 🗺️</a>
  </div>
  <div class="navbar-end flex justify-around md:justify-end mr-4">
    {#if !user}
      <button class="btn btn-primary ml-4" on:click={toToLogin}>Login</button>
      <button class="btn btn-primary ml-4" on:click={toToSignup}>Signup</button>
    {/if}
    {#if user}
      <p>Adventures: {count}</p>
      <UserAvatar {user} />
      <form method="post" action="/" use:enhance>
        <button class="btn btn-primary ml-4">Logout</button>
      </form>
    {/if}
  </div>
</div>
