<!-- routes/signup/+page.svelte -->
<script lang="ts">
  import { enhance } from "$app/forms";
</script>

<h1>Sign up</h1>
<form method="post" use:enhance>
  <label for="username">Username</label>
  <label for="first_name">First Name</label>
  <input name="first_name" id="first_name" /><br />
  <label for="last_name">Last Name</label>
  <input name="last_name" id="last_name" /><br />
  <input name="username" id="username" /><br />
  <label for="password">Password</label>
  <input type="password" name="password" id="password" /><br />
  <button>Continue</button>
</form>
