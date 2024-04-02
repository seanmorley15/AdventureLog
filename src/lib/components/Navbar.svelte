<script lang="ts">
  import { visitCount } from '$lib/utils/stores/visitCountStore';
  import { goto } from '$app/navigation';

    async function goHome() {
        goto('/');
    }
    async function goToLog() {
        goto('/log');
    }
    async function goToFeatured() {
        goto('/featured');
    }


    let count = 0;
    visitCount.subscribe((value) => {
        count = value;
    });

    // Set the visit count to the number of adventures stored in local storage
    const isBrowser = typeof window !== 'undefined';
    if (isBrowser) {
        const storedAdventures = localStorage.getItem('adventures');
        if (storedAdventures) {
            let parsed = JSON.parse(storedAdventures);
            visitCount.set (parsed.length);
        }
}

</script>
<div class="navbar bg-base-100 flex flex-col md:flex-row">
    <div class="navbar-start flex justify-around md:justify-start">
        <button class="btn btn-primary my-2 md:my-0 md:mr-4 md:ml-2" on:click={goHome}>Home</button>
        <button class="btn btn-primary my-2 md:my-0 md:mr-4 md:ml-2" on:click={goToLog}>My Log</button>
        <button class="btn btn-primary my-2 md:my-0" on:click={goToFeatured}>Featured</button>
    </div>
    <div class="navbar-center flex justify-center md:justify-center">
      <a class="btn btn-ghost text-xl" href="/">AdventureLog 🗺️</a>
    </div>
    <div class="navbar-end flex justify-around md:justify-end mr-4">
      <p>Adventures: {count} </p>
    </div>
</div>
