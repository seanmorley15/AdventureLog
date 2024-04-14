<script lang="ts">
    import { countryCodeToName } from "$lib";
    import type { RegionInfo } from "$lib/utils/types.js";

    export let data;
    let info = data.info.data.info as RegionInfo;
    let country = countryCodeToName(data.info.data.country_code);
    let regionName = data.info.data.name;
    let visited = data.visited;
</script>

<h1>Info About {regionName} in {country}</h1>
{#if visited}
    <p>You have visited this region!</p>
{/if}

<h2>Region Info</h2>
{#if info.description}
    <p>{info.description}</p>
{/if}
