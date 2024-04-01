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
<div class="navbar bg-base-100 flex flex-col md:flex-row">
    <div class="navbar-start flex justify-around md:justify-start">
        <button class="btn btn-primary my-2 md:my-0 md:mr-4 md:ml-2" on:click={goHome}>Home</button>
        <button class="btn btn-primary my-2 md:my-0" on:click={goToLog}>My Log</button>
    </div>
    <div class="navbar-center flex justify-center md:justify-center">
      <a class="btn btn-ghost text-xl" href="/">AdventureLog 🗺️</a>
    </div>
    <div class="navbar-end flex justify-around md:justify-end">
      <p>Adventures: {getNumberOfAdventures()} </p>
    </div>
</div>
