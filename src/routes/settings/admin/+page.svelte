<script lang="ts">
  import { enhance } from "$app/forms";
  import { goto } from "$app/navigation";
  import { type SubmitFunction } from "@sveltejs/kit";
  let errors: { message?: string } = {};
  let message: { message?: string } = {};
  let username: string = "";
  let first_name: string = "";
  let last_name: string = "";
  let password: string = "";
  const addUser: SubmitFunction = async ({ formData, action, cancel }) => {
    const response = await fetch(action, {
      method: "POST",
      body: formData,
    });

    if (response.ok) {
      console.log("User Added Successfully!");
      errors = {};
      username = "";
      first_name = "";
      last_name = "";
      password = "";
      cancel();
      return;
    }

    const { type, error } = await response.json();
    if (type === "error") {
      errors = { message: error.message };
    }
    console.log(errors);
    cancel();
  };
</script>

<h1 class="text-center font-extrabold text-4xl">Admin Settings</h1>

<h2 class="text-center font-extrabold text-2xl">Add User</h2>
<div class="flex justify-center">
  <form
    method="POST"
    action="/signup"
    use:enhance={addUser}
    class="w-full max-w-xs"
  >
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
  </form>
</div>

{#if errors.message}
  <div class="text-center text-error mt-4">
    {errors.message}
  </div>
{/if}

<h2 class="text-center font-extrabold text-2xl">Session Managment</h2>
<div class="flex justify-center items-center">
  <form use:enhance method="POST" action="?/clearAllSessions">
    <input
      type="submit"
      class="btn btn-warning"
      value="Clear All Users Sessions"
    />
  </form>
</div>
