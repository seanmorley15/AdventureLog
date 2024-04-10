<script lang="ts">
  import { enhance } from "$app/forms";
  import { goto } from "$app/navigation";
  export let user: any;
  let firstLetter = user.first_name.charAt(0);

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
      <span class="text-2xl -mt-0.5">{firstLetter}</span>
    </div>
  </div>
  <!-- svelte-ignore a11y-missing-attribute -->
  <!-- svelte-ignore a11y-no-noninteractive-tabindex -->
  <ul
    tabindex="0"
    class="dropdown-content z-[1] menu p-2 shadow bg-neutral mt-2 rounded-box w-52"
  >
    <!-- svelte-ignore a11y-missing-attribute -->
    <!-- svelte-ignore a11y-missing-attribute -->
    <li><a>Profile</a></li>
    <li><button on:click={navToLog}>My Log</button></li>
    <li><button on:click={navToSettings}>Settings</button></li>
    <form method="post" action="/" use:enhance>
      <li><button>Logout</button></li>
    </form>
  </ul>
</div>
