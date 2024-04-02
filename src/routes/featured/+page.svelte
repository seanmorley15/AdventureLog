<script lang="ts">
    export let data
    console.log(data.result);
    import FeaturedAdventureCard from '$lib/components/FeaturedAdventureCard.svelte';
    import type { Adventure } from '$lib/utils/types.js';
    import { addAdventure, getNextId } from '../../services/adventureService.js';

    function add(event: CustomEvent<{name: string, location: string}>) {
        console.log(event.detail);
        let newAdventure:Adventure = {
            id: getNextId(),
            name: event.detail.name,
            location: event.detail.location,
            created: ""
        }
        addAdventure(newAdventure);

    }
</script>

<div class="flex justify-center items-center w-full mt-4 mb-4">
    <article class="prose">
        <h1 class="text-center">Featured Adventure Locations</h1>
    </article>
</div>

<div class="grid xl:grid-cols-3 lg:grid-cols-3 md:grid-cols-2 sm:grid-cols-1 gap-4 mt-4 content-center auto-cols-auto ml-6 mr-6">
    {#each data.result as adventure (adventure.id)}
        <FeaturedAdventureCard on:add={add} name={adventure.name} location={adventure.location} />
    {/each}
</div>