<script lang="ts">
    import { goto } from "$app/navigation";
    import AdventureCard from "$lib/components/AdventureCard.svelte";

    export let data: any;
    console.log(data.response);

    async function nav(loc: string) {
        goto(`/worldtravel/${loc}`);
    }
</script>

<h1>Country List</h1>

{#each data.response as item}
    <button class="btn btn-primary" on:click={() => nav(item.country_code)}
        >{item.name}</button
    >
    <!-- <p>Name: {item.name}, Continent: {item.continent}</p> -->
{/each}
