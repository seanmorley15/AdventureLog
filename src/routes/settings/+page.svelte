<script>
    import { enhance } from "$app/forms";

    export let data;
    let username = data.user?.username;
    let first_name = data.user?.first_name;
    let last_name = data.user?.last_name;
    let user_id = data.user?.id;
    let icon = data.user?.icon;
</script>

<h1 class="text-center font-extrabold text-4xl mb-6">Settings Page</h1>

<h1 class="text-center font-extrabold text-xl">User Account Settings</h1>

<div class="flex justify-center">
    <form method="post" use:enhance class="w-full max-w-xs">
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
        <label for="icon">Profile Icon (emoji)</label>
        <input
            type="emoji"
            bind:value={icon}
            name="icon"
            id="icon"
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

<small class="text-center">For Debug Use: UUID={user_id}</small>
