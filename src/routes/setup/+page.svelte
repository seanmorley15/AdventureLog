<script lang="ts">
  import { enhance } from "$app/forms";

  let loading = false;

  function toggleLoad() {
    loading = !loading;
  }
</script>

<h1 class="text-center font-bold text-4xl">AdventureLog Setup</h1>

<!-- centered text descripton welcomeing the user -->
<p class="text-center mt-4">
  Welcome to AdventureLog! Please follow the steps below to setup your server.
</p>

{#if !loading}
  <!-- step 1 create admin user -->
  <h2 class="text-center font-bold text-2xl mt-6">Create Admin User</h2>

  <div class="flex justify-center">
    <form method="post" use:enhance={toggleLoad} class="w-full max-w-xs">
      <label for="username">Username</label>
      <input
        name="username"
        id="username"
        class="block mb-2 input input-bordered w-full max-w-xs"
      /><br />
      <label for="first_name">First Name</label>
      <input
        name="first_name"
        id="first_name"
        class="block mb-2 input input-bordered w-full max-w-xs"
      /><br />
      <label for="last_name">Last Name</label>
      <input
        name="last_name"
        id="last_name"
        class="block mb-2 input input-bordered w-full max-w-xs"
      /><br />
      <label for="password">Password</label>
      <input
        type="password"
        name="password"
        id="password"
        class="block mb-2 input input-bordered w-full max-w-xs"
      /><br />
      <button class="py-2 px-4 btn btn-primary">Signup and Setup Server</button>
    </form>
  </div>
{/if}

{#if loading}
  <div class="flex justify-center items-center w-full mt-16">
    <span class="loading loading-spinner w-24 h-24"></span>
  </div>
{/if}

<svelte:head>
  <title>Setup | AdventureLog</title>
  <meta
    name="description"
    content="Setup AdventureLog with your admin account"
  />
</svelte:head>
