<script lang="ts">
    export let data;
    import AdventureCard from "$lib/components/AdventureCard.svelte";
    import { countryCodeToName } from "$lib";
    import { getFlag } from "$lib";
    import { goto } from "$app/navigation";
    import { onMount } from "svelte";

    function markVisited(event: { detail: string }) {
        console.log(`Marked ${event.detail} as visited`);
        fetch("/api/regionvisit", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                region_id: event.detail,
            }),
        }).then((response) => {
            if (response.status === 401) {
                goto("/login");
            }
            return response.json();
        });
    }

    function removeVisit(event: { detail: string }) {
        console.log(`Removed visit to ${event.detail}`);
        fetch("/api/regionvisit", {
            method: "DELETE",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                region_id: event.detail,
            }),
        }).then((response) => {
            if (response.status === 401) {
                goto("/login");
            }
            return response.json();
        });
    }

    onMount(() => {
        console.log(data.visitedRegions);
    });
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
    {#each data.regions as region (region.id)}
        <AdventureCard
            type="worldtravelregion"
            regionId={region.id}
            name={region.name}
            on:markVisited={markVisited}
            visited={data.visitedRegions.some(
                (visitedRegion) => visitedRegion.region_id === region.id,
            )}
            on:removeVisit={removeVisit}
        />
    {/each}
</div>
