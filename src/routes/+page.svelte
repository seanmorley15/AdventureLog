<script lang="ts">
    import AdventureCard from "$lib/components/AdventureCard.svelte";
    import type { Adventure } from '$lib/utils/types';
    import { addAdventure, getAdventures, getNextId, removeAdventure ,saveEdit } from "../services/adventureService";
    import { onMount } from 'svelte';

    let newName = '';
    let newLocation = '';

    let editId:number = NaN;
    let editName:string = '';
    let editLocation:string = '';
    let editCreated: string = '';

    let adventures: Adventure[] = [];

    const createNewAdventure = () => {
        let currentDate = new Date();
        let dateString = currentDate.toISOString().slice(0,10); // Get date in "yyyy-mm-dd" format
        const newAdventure: Adventure = { id:getNextId(), name: newName, location: newLocation, created: dateString};
        addAdventure(newAdventure);
        newName = ''; // Reset newName and newLocation after adding adventure
        newLocation = '';
        adventures = getAdventures(); // add to local array
    };

    onMount(async () => {
		adventures = getAdventures()
	});

    function triggerRemoveAdventure(event: { detail: string; }) {
        removeAdventure(event)
        adventures = getAdventures()
    }

    function saveAdventure() {
        saveEdit(editId, editName, editLocation, editCreated)
        adventures = getAdventures()
    }

    function editAdventure(event: { detail: number; }) {
        const adventure = adventures.find(adventure => adventure.id === event.detail);
        if (adventure) {
            editId = adventure.id;
            editName = adventure.name;
            editLocation = adventure.location;
            editCreated = adventure.created;
        }
    }
    
</script>

<input bind:value={newName} placeholder="Adventure Name" />
<input bind:value={newLocation} placeholder="Adventure Location" />
<button on:click={createNewAdventure}>Add Adventure</button>

{#each adventures as adventure, i}
    <div>
        <AdventureCard id={adventure.id} name={adventure.name} location={adventure.location} created={adventure.created} on:remove={triggerRemoveAdventure} on:edit={editAdventure} />
    </div>
{/each}

{#if editId !== null}
    <form on:submit|preventDefault={saveAdventure}>
        <input bind:value={editName} />
        <input bind:value={editLocation} />
        <input type="date" bind:value={editCreated} />
        <button type="submit">Save</button>
    </form>
{/if}

<style>

</style>