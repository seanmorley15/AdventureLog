<script lang="ts">
    import { goto } from "$app/navigation";
    import AdventureCard from "$lib/components/AdventureCard.svelte";

    export let data: any;

    async function nav(loc: string) {
        goto(`/worldtravel/${loc}`);
    }
    function getFlag(country: string) {
        return `https://flagcdn.com/h24/${country}.png`;
    }
</script>

<h1 class="text-center font-bold text-4xl mb-4">Country List</h1>

{#each data.response as item}
    <button
        class="btn btn-primary mr-4 mb-2"
        on:click={() => nav(item.country_code)}
        >{item.name}
        <img
            src={getFlag(item.country_code)}
            class="inline-block -mt-1 mr-1"
            alt="Flag"
        /></button
    >
    <!-- <p>Name: {item.name}, Continent: {item.continent}</p> -->
{/each}
