<script lang="ts">
  import { page } from "$app/stores";

  import { enhance } from "$app/forms";
  import UserCard from "$lib/components/UserCard.svelte";

  let username: string = "";
  let first_name: string = "";
  let last_name: string = "";
  let password: string = "";
  import ConfirmModal from "$lib/components/ConfirmModal.svelte";

  let isModalOpen = false;

  async function clearAllSessions() {
    await fetch("?/clearAllSessions", {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: new URLSearchParams(),
    });
    window.location.reload();
  }

  function openModal() {
    isModalOpen = true;
  }
  function closeModal() {
    isModalOpen = false;
  }

  let visitCount = $page.data.visitCount[0].count;
  let userCount = $page.data.userCount[0].count;
  let regionCount = $page.data.regionCount[0].count;
  let tripCount = $page.data.tripCount[0].count;
  let planCount = $page.data.planCount[0].count;
  let featuredCount = $page.data.featuredCount[0].count;
</script>

<h1 class="text-center font-extrabold text-4xl">Admin Settings</h1>

<h2 class="text-center font-extrabold text-2xl">Add User</h2>
<div class="flex justify-center mb-4">
  <form method="POST" class="w-full max-w-xs" use:enhance action="?/adduser">
    <label for="username">Username</label>
    <input
      name="username"
      id="username"
      bind:value={username}
      class="block mb-2 input input-bordered w-full max-w-xs"
    /><br />
    <label for="first_name">First Name</label>
    <input
      name="first_name"
      id="first_name"
      bind:value={first_name}
      class="block mb-2 input input-bordered w-full max-w-xs"
    /><br />
    <label for="last_name">Last Name</label>
    <input
      name="last_name"
      id="last_name"
      bind:value={last_name}
      class="block mb-2 input input-bordered w-full max-w-xs"
    /><br />
    <label for="password">Password</label>
    <input
      type="password"
      name="password"
      id="password"
      bind:value={password}
      class="block mb-2 input input-bordered w-full max-w-xs"
    /><br />
    <label for="role">Admin User?</label>
    <input
      type="checkbox"
      name="role"
      id="admin"
      class="block mb-2 checkbox-primary checkbox"
    /><br />
    <button class="py-2 px-4 btn btn-primary">Signup</button>
    {#if $page.form?.message}
      <div class="text-center text-error mt-4">
        {$page.form?.message}
      </div>
    {/if}
    {#if $page.form?.success}
      <div class="text-center text-success mt-4">User added successfully!</div>
    {/if}
  </form>
</div>

<h2 class="text-center font-extrabold text-2xl mb-2">Session Managment</h2>
<div class="flex justify-center items-center">
  <button on:click={openModal} class="btn btn-warning mb-4"
    >Clear All Users Sessions</button
  >
</div>

<h2 class="text-center font-extrabold text-2xl">User Managment</h2>
<div
  class="grid xl:grid-cols-3 lg:grid-cols-3 md:grid-cols-2 sm:grid-cols-1 gap-4 mt-4 content-center auto-cols-auto ml-6 mr-6 mb-4"
>
  {#each $page.data.users as user}
    <div>
      <UserCard {user} />
    </div>
  {/each}
</div>

{#if isModalOpen}
  <ConfirmModal
    on:close={closeModal}
    on:confirm={clearAllSessions}
    title="Clear All Sessions"
    isWarning={true}
    message="Are you sure you want to clear all user sessions?"
  />
{/if}

<h2 class="text-center font-extrabold text-2xl">Admin Stats (All Users)</h2>
<div class="flex items-center justify-center mb-4">
  <div class="stats stats-vertical lg:stats-horizontal shadow">
    <div class="stat">
      <div class="stat-title">Total Visits</div>
      <div class="stat-value text-center">{visitCount}</div>
    </div>

    <div class="stat">
      <div class="stat-title">Total Users</div>
      <div class="stat-value text-center">{userCount}</div>
    </div>

    <div class="stat">
      <div class="stat-title">Visited Regions</div>
      <div class="stat-value text-center">{regionCount}</div>
    </div>
    <div class="stat">
      <div class="stat-title">Total Trips</div>
      <div class="stat-value text-center">{tripCount}</div>
    </div>
    <div class="stat">
      <div class="stat-title">Total Plans</div>
      <div class="stat-value text-center">{planCount}</div>
    </div>
    <div class="stat">
      <div class="stat-title">Featured Adventures</div>
      <div class="stat-value text-center">{featuredCount}</div>
    </div>
  </div>
</div>

<svelte:head>
  <title>Admin Settings | AdventureLog</title>
  <meta
    name="description"
    content="Admin Settings for AdventureLog. Add users, manage sessions, and more!"
  />
</svelte:head>
