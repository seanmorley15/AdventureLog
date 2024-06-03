<script lang="ts">
  import { enhance } from "$app/forms";
  import { goto } from "$app/navigation";
  export let user: any;
  import UserAvatar from "./UserAvatar.svelte";
  import InfoModal from "./InfoModal.svelte";
  import type { SubmitFunction } from "@sveltejs/kit";
  import { onMount } from "svelte";

  let searchVal: string = "";

  async function toToLogin() {
    goto("/login");
  }
  async function goToSignup() {
    goto("/signup");
  }

  onMount(() => {
    if (window.location.pathname === "/search") {
      searchVal = new URLSearchParams(window.location.search).get("all") || "";
    }
  });

  async function goToSearch() {
    let reload: boolean = false;
    if (window.location.pathname === "/search") {
      reload = true;
    }
    await goto("/search?all=" + searchVal);
    if (reload) {
      location.reload();
    }
  }

  const submitUpdateTheme: SubmitFunction = ({ action }) => {
    const theme = action.searchParams.get("theme");
    if (theme) {
      document.documentElement.setAttribute("data-theme", theme);
    }
  };

  let count = 0;

  let isInfoModalOpen = false;

  // Set the visit count to the number of adventures stored in local storage
  const isBrowser = typeof window !== "undefined";
  if (isBrowser) {
    const storedAdventures = localStorage.getItem("adventures");
  }
</script>

{#if isInfoModalOpen}
  <InfoModal on:close={() => (isInfoModalOpen = false)} />
{/if}

<div class="navbar bg-base-100">
  <div class="navbar-start">
    <div class="dropdown">
      <div tabindex="0" role="button" class="btn btn-ghost lg:hidden">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="h-5 w-5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          ><path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M4 6h16M4 12h8m-8 6h16"
          /></svg
        >
      </div>
      <!-- svelte-ignore a11y-no-noninteractive-tabindex -->
      <ul
        tabindex="0"
        class="menu menu-sm dropdown-content mt-3 z-[1] p-2 shadow bg-base-100 rounded-box w-52 gap-2"
      >
        {#if user}
          <li>
            <button on:click={() => goto("/log")}>My Log</button>
          </li>
          <li>
            <button on:click={() => goto("/planner")}>Planner</button>
          </li>
        {/if}
        <li>
          <button on:click={() => goto("/worldtravel")}>World Travel</button>
        </li>
        <li>
          <button on:click={() => goto("/featured")}>Featured</button>
        </li>
        {#if user}
          <li>
            <label class="input input-bordered flex items-center gap-2">
              <input type="text" class="grow" placeholder="Search" />
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 16 16"
                fill="currentColor"
                class="w-4 h-4 opacity-70"
                ><path
                  fill-rule="evenodd"
                  d="M9.965 11.026a5 5 0 1 1 1.06-1.06l2.755 2.754a.75.75 0 1 1-1.06 1.06l-2.755-2.754ZM10.5 7a3.5 3.5 0 1 1-7 0 3.5 3.5 0 0 1 7 0Z"
                  clip-rule="evenodd"
                /></svg
              >
            </label>
          </li>
        {/if}
        {#if !user}
          <li>
            <button class="btn btn-primary" on:click={toToLogin}>Login</button>
          </li>
          <li>
            <button class="btn btn-primary" on:click={goToSignup}>Signup</button
            >
          </li>
        {/if}
      </ul>
    </div>
    <a class="btn btn-ghost text-xl" href="/"
      >AdventureLog <img src="/favicon.png" alt="Map Logo" class="w-8" /></a
    >
  </div>
  <div class="navbar-center hidden lg:flex">
    <ul class="menu menu-horizontal px-1 gap-2">
      {#if user}
        <li>
          <button class="btn btn-neutral" on:click={() => goto("/log")}
            >My Log</button
          >
        </li>
        <li>
          <button class="btn btn-neutral" on:click={() => goto("/planner")}
            >Planner</button
          >
        </li>
      {/if}
      <li>
        <button class="btn btn-neutral" on:click={() => goto("/worldtravel")}
          >World Travel</button
        >
      </li>
      <li>
        <button class="btn btn-neutral" on:click={() => goto("/featured")}
          >Featured</button
        >
      </li>
      {#if user}
        <li>
          <label class="input input-bordered flex items-center gap-2">
            <form on:submit={() => goto("/search?all=" + searchVal)}>
              <input
                type="text"
                class="grow"
                placeholder="Search"
                bind:value={searchVal}
                on:keydown={(event) => {
                  if (event.key === "Enter") {
                    event.preventDefault();

                    goToSearch();
                  }
                }}
              />
            </form>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 16 16"
              fill="currentColor"
              class="w-4 h-4 opacity-70"
              ><path
                fill-rule="evenodd"
                d="M9.965 11.026a5 5 0 1 1 1.06-1.06l2.755 2.754a.75.75 0 1 1-1.06 1.06l-2.755-2.754ZM10.5 7a3.5 3.5 0 1 1-7 0 3.5 3.5 0 0 1 7 0Z"
                clip-rule="evenodd"
              /></svg
            >
          </label>
        </li>
      {/if}
      {#if !user}
        <li>
          <button class="btn btn-primary" on:click={toToLogin}>Login</button>
        </li>
        <li>
          <button class="btn btn-primary" on:click={goToSignup}>Signup</button>
        </li>
      {/if}
    </ul>
  </div>
  <div class="navbar-end">
    {#if user}
      <UserAvatar {user} />
    {/if}
    <div class="dropdown dropdown-bottom dropdown-end">
      <div tabindex="0" role="button" class="btn m-1 ml-4">
        <iconify-icon icon="mdi:dots-horizontal" class="text-xl"></iconify-icon>
      </div>
      <!-- svelte-ignore a11y-no-noninteractive-tabindex -->
      <ul
        tabindex="0"
        class="dropdown-content z-[1] menu p-2 shadow bg-base-100 rounded-box w-52"
      >
        <button class="btn" on:click={() => (isInfoModalOpen = true)}
          >About AdventureLog</button
        >
        <p class="font-bold m-4 text-lg">Theme Selection</p>
        <form method="POST" use:enhance={submitUpdateTheme}>
          <li>
            <button formaction="/?/setTheme&theme=light"
              >Light<iconify-icon icon="mdi:weather-sunny" class="text-xl"
              ></iconify-icon></button
            >
          </li>
          <li>
            <button formaction="/?/setTheme&theme=dark"
              >Dark<iconify-icon icon="mdi:weather-night" class="text-xl"
              ></iconify-icon></button
            >
          </li>
          <li>
            <button formaction="/?/setTheme&theme=night"
              >Night<iconify-icon icon="mdi:weather-night" class="text-xl"
              ></iconify-icon></button
            >
          </li>
          <!-- <li><button formaction="/?/setTheme&theme=nord">Nord</button></li> -->
          <!-- <li><button formaction="/?/setTheme&theme=retro">Retro</button></li> -->
          <li>
            <button formaction="/?/setTheme&theme=forest"
              >Forest<iconify-icon icon="mdi:forest" class="text-xl"
              ></iconify-icon></button
            >
            <button formaction="/?/setTheme&theme=garden"
              >Garden<iconify-icon icon="mdi:flower" class="text-xl"
              ></iconify-icon></button
            >
            <button formaction="/?/setTheme&theme=aqua"
              >Aqua<iconify-icon icon="mdi:water" class="text-xl"
              ></iconify-icon></button
            >
          </li>
        </form>
      </ul>
    </div>
  </div>
</div>
