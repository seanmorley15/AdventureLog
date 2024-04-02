<script lang="ts">
    import AdventureCard from "$lib/components/AdventureCard.svelte";
    import type { Adventure } from '$lib/utils/types';
    import { addAdventure, clearAdventures, getAdventures, getNextId, removeAdventure ,saveEdit } from "../../services/adventureService";
    import { onMount } from 'svelte';
    import { exportData } from "../../services/export";
    import { importData } from "../../services/import";
    import exportFile from "$lib/assets/exportFile.svg";
    import deleteIcon from "$lib/assets/deleteIcon.svg";
    import SucessToast from "$lib/components/SucessToast.svelte";
    import mapDrawing from "$lib/assets/adventure_map.svg"
    import EditModal from "$lib/components/EditModal.svelte";

    let newName = '';
    let newLocation = '';

    let editId:number = NaN;
    let editName:string = '';
    let editLocation:string = '';
    let editCreated: string = '';

    let adventures: Adventure[] = [];

    let isShowingToast:boolean = false;
    let toastAction:string = '';

    function showToast(action:string) {
        toastAction = action;
        isShowingToast = true;
        console.log('showing toast');

        setTimeout(() => {
            isShowingToast = false;
            toastAction = '';
            console.log('hiding toast');
        }, 3000);
    }

    const createNewAdventure = () => {
        let currentDate = new Date();
        let dateString = currentDate.toISOString().slice(0,10); // Get date in "yyyy-mm-dd" format
        const newAdventure: Adventure = { id:getNextId(), name: newName, location: newLocation, created: dateString};
        addAdventure(newAdventure);
        newName = ''; // Reset newName and newLocation after adding adventure
        newLocation = '';
        adventures = getAdventures(); // add to local array
        showToast('added');
    };

    onMount(async () => {
		adventures = getAdventures()
	});

    function triggerRemoveAdventure(event: { detail: number; }) {
        removeAdventure(event)
        showToast('removed');
        adventures = getAdventures()
    }

    function saveAdventure(event: { detail: Adventure; }) {
        console.log("Event" + event.detail)
        saveEdit(event.detail)
        editId = NaN;
        editName = '';
        editLocation = '';
        editCreated = '';
        adventures = getAdventures()
        showToast('edited');

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

    function handleClose() {
        editId = NaN;
        editName = '';
        editLocation = '';
        editCreated = '';
    }

    function deleteData() {
        clearAdventures();
        adventures = getAdventures();
        showToast('deleted');
    }

</script>

<div class="flex justify-center items-center w-full mt-4 mb-4">
    <article class="prose">
        <h2 class="text-center">Add new Location</h2>
    </article>
</div>

<div class="flex flex-row items-center justify-center gap-4">
    <form on:submit={createNewAdventure} class="flex gap-2">
        <input type="text" bind:value={newName} placeholder="Adventure Name" class="input input-bordered w-full max-w-xs" />
        <input type="text" bind:value={newLocation} placeholder="Adventure Location" class="input input-bordered w-full max-w-xs" />
        <input class="btn btn-primary" type="submit" value="Add Adventure">
    </form>
</div>

<div class="flex justify-center items-center w-full mt-4 mb-4">
    <article class="prose">
        <h1 class="text-center">My Visited Adventure Locations</h1>
    </article>
</div>


{#if isShowingToast}
    <SucessToast action={toastAction} />
{/if}

{#if !Number.isNaN(editId)}
<EditModal bind:editId={editId} bind:editName={editName} bind:editLocation={editLocation} bind:editCreated={editCreated} on:submit={saveAdventure} on:close={handleClose} />
{/if}

<div class="grid xl:grid-cols-3 lg:grid-cols-3 md:grid-cols-2 sm:grid-cols-1 gap-4 mt-4 content-center auto-cols-auto ml-6 mr-6">
    {#each adventures as adventure (adventure.id)}
        <AdventureCard id={adventure.id} name={adventure.name} location={adventure.location} created={adventure.created} on:remove={triggerRemoveAdventure} on:edit={editAdventure} />
    {/each}
</div>

{#if adventures.length == 0}
<div class="flex flex-col items-center justify-center  mt-16">
    <article class="prose mb-4"><h2>Add some adventures!</h2></article>
    <img src={mapDrawing} width="25%" alt="Logo" />
</div>
{/if}

{#if adventures.length != 0}
<div class="flex flex-row items-center justify-center mt-16 gap-4 mb-4">
    <button class="btn btn-neutral" on:click={async () => { window.location.href = exportData(); }}>
        <img src={exportFile} class="inline-block -mt-1" alt="Logo" /> Save as File
    </button>
    <button class="btn btn-neutral" on:click={deleteData}>
        <img src={deleteIcon} class="inline-block -mt-1" alt="Logo" /> Delete Data
    </button>
</div>
{/if}
