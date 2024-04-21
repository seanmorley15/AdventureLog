<script lang="ts">
  import type { DatabaseUser } from "$lib/server/auth";

  export let user: DatabaseUser;
</script>

<div class="card w-96 bg-base-100 shadow-xl">
  <div class="card-body">
    <h2 class="card-title">{user.first_name} {user.last_name}</h2>
    <p>{user.username}</p>
    <p>Last Login: {user.last_login}</p>
    <p>Created: {user.signup_date}</p>
    <div class="card-actions justify-end">
      <button class="btn btn-primary">Edit User</button>
    </div>
  </div>
</div>
