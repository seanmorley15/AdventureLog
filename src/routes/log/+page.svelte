<script lang="ts">
    import AdventureCard from "$lib/components/AdventureCard.svelte";
    import type { Adventure } from '$lib/utils/types';
    import { addAdventure, getAdventures, getNextId, removeAdventure ,saveEdit } from "../../services/adventureService";
    import { onMount } from 'svelte';
    import { exportData } from "../../services/export";
    import { importData } from "../../services/import";
    import exportFile from "$lib/assets/exportFile.svg";

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

<div class="flex flex-row items-center justify-center gap-4">
    <input type="text" bind:value={newName} placeholder="Adventure Name" class="input input-bordered w-full max-w-xs" />
    <input type="text" bind:value={newLocation} placeholder="Adventure Location" class="input input-bordered w-full max-w-xs" />
    <button class="btn" on:click={createNewAdventure}>Add Adventure</button>
</div>



{#each adventures as adventure, i}
    <div>
        <AdventureCard id={adventure.id} name={adventure.name} location={adventure.location} created={adventure.created} on:remove={triggerRemoveAdventure} on:edit={editAdventure} />
    </div>
{/each}

{#if adventures.length == 0}
<div class="flex flex-col items-center justify-center mt-28">
    <article class="prose mb-4"><h2>Add some adventures!</h2></article>
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



<button class="btn btn-neutral ml-auto mr-auto block" on:click={async () => { window.location.href = exportData(); }}>
    <img src={exportFile} class="inline-block -mt-1" alt="Logo" /> Save as File
</button>

{/if}

<!-- <style>
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
</style> -->