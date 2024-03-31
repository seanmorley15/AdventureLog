<script lang="ts">
  import { getNumberOfAdventures } from "../../services/adventureService";
  import { goto } from '$app/navigation';

    async function goHome() {
        goto('/');
    }
    async function goToLog() {
        goto('/log');
    }
</script>
<div class="navbar bg-base-100">
    <div class="navbar-start">
        <button class="btn btn-primary mr-4 ml-2" on:click={goHome}>Home</button>
        <button class="btn btn-primary" on:click={goToLog}>My Log</button>
    </div>
    <div class="navbar-center">
      <a class="btn btn-ghost text-xl" href="/">AdventureLog 🗺️</a>
    </div>
    <div class="navbar-end">
      <p>Adventures: {getNumberOfAdventures()} </p>
    </div>
  </div>
