<script lang="ts">
    import { enhance } from "$app/forms";
</script>

<h1 class="text-center font-bold text-4xl">AdventureLog Setup</h1>

<!-- centered text descripton welcomeing the user -->
<p class="text-center mt-4">
    Welcome to AdventureLog! Please follow the steps below to setup your server.
</p>

<!-- step 1 create admin user -->
<h2 class="text-center font-bold text-2xl mt-6">Create Admin User</h2>

<div class="flex justify-center">
    <form method="post" use:enhance class="w-full max-w-xs">
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
        <button class="py-2 px-4 btn btn-primary">Signup</button>
    </form>
</div>
