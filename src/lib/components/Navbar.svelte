<script lang="ts">
  import { enhance } from "$app/forms";
  import { visitCount } from "$lib/utils/stores/visitCountStore";
  import { goto } from "$app/navigation";
  import type { DatabaseUser } from "$lib/server/auth";
  export let user: any;
  import UserAvatar from "./UserAvatar.svelte";
  import { onMount } from "svelte";
  import InfoModal from "./InfoModal.svelte";
  import infoIcon from "$lib/assets/info.svg";
  import type { SubmitFunction } from "@sveltejs/kit";
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
  async function goToSignup() {
    goto("/signup");
  }
  async function goToWorldTravel() {
    goto("/worldtravel");
  }

  const submitUpdateTheme: SubmitFunction = ({ action }) => {
    const theme = action.searchParams.get("theme");
    if (theme) {
      document.documentElement.setAttribute("data-theme", theme);
    }
  };

  let count = 0;

  let infoModalOpen = false;

  function showModal() {
    infoModalOpen = true;
  }

  function closeModal() {
    infoModalOpen = false;
  }

  // get value from fetch /api/visitcount

  $: if (user) {
    onMount(async () => {
      const res = await fetch("/api/visitcount");
      const data = await res.json();
      visitCount.set(data.visitCount);
    });
  }

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
      <button class="btn btn-primary my-2 md:my-0 md:mr-4" on:click={goToLog}
        >My Log</button
      >
    {/if}
    <button
      class="btn btn-primary my-2 md:my-0 md:mr-4"
      on:click={goToWorldTravel}>World Tavel Log</button
    >
    <button class="btn btn-primary my-2 md:my-0" on:click={goToFeatured}
      >Featured</button
    >
  </div>
  <div class="navbar-center flex justify-center md:justify-center">
    <a class="btn btn-ghost text-xl" href="/">AdventureLog 🗺️</a>
  </div>

  {#if infoModalOpen}
    <InfoModal on:close={closeModal} />
  {/if}
  <div class="navbar-end flex justify-around md:justify-end mr-4">
    {#if !user}
      <button class="btn btn-primary ml-4" on:click={toToLogin}>Login</button>
      <button class="btn btn-primary ml-4" on:click={goToSignup}>Signup</button>
    {/if}

    {#if user}
      <p class="font-bold">Adventures: {count}</p>
      <UserAvatar {user} />
    {/if}
    <button class="btn btn-neutral ml-4" on:click={showModal}>About</button>
    <div class="dropdown dropdown-bottom dropdown-end">
      <div tabindex="0" role="button" class="btn m-1 ml-4">Themes</div>
      <!-- svelte-ignore a11y-no-noninteractive-tabindex -->
      <ul
        tabindex="0"
        class="dropdown-content z-[1] menu p-2 shadow bg-base-100 rounded-box w-52"
      >
        <form method="POST" use:enhance={submitUpdateTheme}>
          <li><button formaction="/?/setTheme&theme=light">Light</button></li>
          <li><button formaction="/?/setTheme&theme=dark">Dark</button></li>
          <li><button formaction="/?/setTheme&theme=night">Night</button></li>
          <!-- <li><button formaction="/?/setTheme&theme=nord">Nord</button></li> -->
          <!-- <li><button formaction="/?/setTheme&theme=retro">Retro</button></li> -->
          <li><button formaction="/?/setTheme&theme=forest">Forest</button></li>
        </form>
      </ul>
    </div>
  </div>
</div>
