<script lang="ts">
    export let data;
    import AdventureCard from "$lib/components/AdventureCard.svelte";
    import { countryCodeToName } from "$lib";
    import { getFlag } from "$lib";
</script>

<h1 class="text-center text-4xl font-bold">
    Regions in {countryCodeToName(data.countrycode)}
    <img
        src={getFlag(40, data.countrycode)}
        class="inline-block -mt-1 mr-1"
        alt="Flag"
    />
</h1>

<div
    class="grid xl:grid-cols-3 lg:grid-cols-3 md:grid-cols-2 sm:grid-cols-1 gap-4 mt-4 content-center auto-cols-auto ml-6 mr-6"
>
    {#each data.regions as region}
        <AdventureCard type="worldtravelregion" name={region.name} />
    {/each}
</div>
