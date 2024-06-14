<script lang="ts">
  import { enhance } from "$app/forms";
  import { goto } from "$app/navigation";
  export let user: any;

  async function navToSettings() {
    goto("/settings");
  }
  async function navToLog() {
    goto("/log");
  }
</script>

<div class="dropdown dropdown-bottom dropdown-end" tabindex="0" role="button">
  <div class="avatar placeholder">
    <div class="bg-neutral text-neutral-content rounded-full w-10 ml-4">
      {#if user.icon}
        <img src={`/cdn/profile-pics/${user.icon}`} alt="" />
      {:else}
        <span class="text-2xl -mt-1">{user.first_name[0]}</span>
      {/if}
    </div>
  </div>
  <!-- svelte-ignore a11y-missing-attribute -->
  <!-- svelte-ignore a11y-no-noninteractive-tabindex -->
  <ul
    tabindex="0"
    class="dropdown-content z-[1] menu p-2 shadow bg-primary-content mt-2 rounded-box w-52"
  >
    <!-- svelte-ignore a11y-missing-attribute -->
    <!-- svelte-ignore a11y-missing-attribute -->
    <p class="text-lg ml-4 font-bold">Hi, {user.first_name} {user.last_name}</p>
    <li><button on:click={() => goto("/profile")}>Profile</button></li>
    <li><button on:click={navToLog}>My Log</button></li>
    <li><button on:click={navToSettings}>User Settings</button></li>
    {#if user.role == "admin"}
      <li>
        <button on:click={() => goto("/settings/admin")}>Admin Settings</button>
      </li>
    {/if}

    <form method="post">
      <li><button formaction="/?/logout">Logout</button></li>
    </form>
  </ul>
</div>
