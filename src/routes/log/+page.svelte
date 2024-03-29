<script lang="ts">
    import AdventureCard from "$lib/components/AdventureCard.svelte";
    import type { Adventure } from '$lib/utils/types';
    import { addAdventure, getAdventures, getNextId, removeAdventure ,saveEdit } from "../../services/adventureService";
    import { onMount } from 'svelte';
    import { exportData } from "../../services/export";
    import { importData } from "../../services/import";

    import mapDrawing from "$lib/assets/adventure_map.svg"


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

    function triggerRemoveAdventure(event: { detail: number; }) {
        removeAdventure(event)
        adventures = getAdventures()
    }

    function saveAdventure() {
        saveEdit(editId, editName, editLocation, editCreated)
        editId = NaN;
        editName = '';
        editLocation = '';
        editCreated = '';
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

{#if adventures.length == 0}
<div class="addsomething">
    <h2>Add some adventures!</h2>
    <img src={mapDrawing} width="25%" alt="Logo" />
</div >

{/if}

{#if !Number.isNaN(editId)}
    <form on:submit|preventDefault={saveAdventure}>
        <input bind:value={editName} />
        <input bind:value={editLocation} />
        <input type="date" bind:value={editCreated} />
        <button type="submit">Save</button>
    </form>
{/if}

{#if adventures.length != 0}
<button on:click={async () => { window.location.href = exportData(); }}>Save as File</button>
{/if}

<style>
.addsomething {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    height: 90vh;
    text-align: center;
}
button {
        margin-left: 1rem;
        padding: 0.5rem 1rem;
        border: none;
        border-radius: 4px;
        background-color: #076836;
        color: white;
        cursor: pointer;
        transition: background-color 0.3s ease;
        box-shadow: 0px 2px 5px rgba(0,0,0,0.1);
    }

    button:hover {
        background-color: #074b28;
    }
</style>