<script lang="ts">
  import { enhance } from "$app/forms";

  export let data;

  let username = data.user?.username;
  let first_name = data.user?.first_name;
  let last_name = data.user?.last_name;
  let user_id = data.user?.id;
  let icon = data.user?.icon;
  let signup_date = data.user?.signup_date;
  let role = data.user?.role;
  console.log(username);
  let file: File | null = null;

  // the submit function shoud just reload the page
</script>

<h1 class="text-center font-extrabold text-4xl mb-6">Settings Page</h1>

<h1 class="text-center font-extrabold text-xl">User Account Settings</h1>
<div class="flex justify-center">
  <form
    method="post"
    use:enhance
    class="w-full max-w-xs"
    enctype="multipart/form-data"
  >
    <label for="username">Username</label>
    <input
      bind:value={username}
      name="username"
      id="username"
      class="block mb-2 input input-bordered w-full max-w-xs"
    /><br />
    <label for="first_name">First Name</label>
    <input
      type="text"
      bind:value={first_name}
      name="first_name"
      id="first_name"
      class="block mb-2 input input-bordered w-full max-w-xs"
    /><br />
    <label for="last_name">Last Name</label>
    <input
      type="text"
      bind:value={last_name}
      name="last_name"
      id="last_name"
      class="block mb-2 input input-bordered w-full max-w-xs"
    /><br />
    <label for="profilePicture">Profile Picture</label>
    <input
      type="file"
      bind:value={file}
      name="profilePicture"
      id="profilePicture"
      class="block mb-2 input input-bordered w-full max-w-xs"
    /><br />
    <label for="password">Password</label>
    <input
      type="password"
      name="password"
      id="password"
      class="block mb-2 input input-bordered w-full max-w-xs"
    /><br />
    <!--  make hidden input where the user id is -->
    <input
      type="hidden"
      bind:value={user_id}
      name="user_id"
      id="user_id"
      class="block mb-2 input input-bordered w-full max-w-xs"
    />
    <button class="py-2 px-4 btn btn-primary">Update</button>
  </form>
</div>

<small class="text-center"
  ><b>For Debug Use:</b> UUID={user_id} Signup Date={signup_date} Role={role}</small
>

<svelte:head>
  <title>User Settings | AdventureLog</title>
  <meta
    name="description"
    content="Update your user account settings here. Change your username, first name, last name, and profile icon."
  />
</svelte:head>
