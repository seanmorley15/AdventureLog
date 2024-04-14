<script lang="ts">
    import { countryCodeToName } from "$lib";
    import type { RegionInfo } from "$lib/utils/types.js";

    export let data;
    let info = data.info.data.info as RegionInfo;
    let country = countryCodeToName(data.info.data.country_code);
    let regionName = data.info.data.name;
    let visited = data.visited;
</script>

{#if info}
    <div class="flex justify-center content-center text-center">
        <article class="prose">
            <h1>Info About {regionName} in {country}</h1>
            {#if visited}
                <p>You have visited this region!</p>
            {/if}

            <h2>Region Info</h2>
            {#if info.description}
                <p>{info.description}</p>
            {/if}
            {#if info.capital}
                <p><b>Capital:</b> {info.capital}</p>
            {/if}
            {#if info.population}
                <p>
                    <b>Population:</b>
                    {info.population.estimate} ({info.population.year})
                </p>
            {/if}
            {#if info.area}
                <p><b>Area:</b> {info.area.total} {info.area.units}</p>
            {/if}
            {#if info.state_flower}
                <p><b>State Flower:</b> {info.state_flower}</p>
            {/if}
            {#if info.state_bird}
                <p><b>State Bird:</b> {info.state_bird}</p>
            {/if}
            {#if info.state_tree}
                <p><b>State Tree:</b> {info.state_tree}</p>
            {/if}
            {#if info.climate}
                <p><b>Climate:</b> {info.climate.description}</p>
                <p><b>Summer Highs:</b> {info.climate.summer_highs}</p>
                <p><b>Winter Lows:</b> {info.climate.winter_lows}</p>
                <p><b>Precipitation:</b> {info.climate.precipitation}</p>
            {/if}
            {#if info.economy}
                {#if info.economy.industries && info.economy.industries.length}
                    <p>
                        <b>Industries:</b>
                        {info.economy.industries.join(", ")}
                    </p>
                {/if}
                {#if info.economy.agricultural_products && info.economy.agricultural_products.length}
                    <p>
                        <b>Agricultural Products:</b>
                        {info.economy.agricultural_products.join(", ")}
                    </p>
                {/if}
            {/if}
            {#if info.tourism}
                {#if info.tourism.attractions && info.tourism.attractions.length}
                    <p>
                        <b>Tourism Attractions:</b>
                        {info.tourism.attractions.join(", ")}
                    </p>
                {/if}
            {/if}
            {#if info.major_sports_teams && info.major_sports_teams.length}
                <p>
                    <b>Major Sports Teams:</b>
                    {info.major_sports_teams.join(", ")}
                </p>
            {/if}
        </article>
    </div>
{:else}
    <div class="flex justify-center content-center text-center">
        <article class="prose">
            <h1>Region Not Found</h1>
            <p>Sorry, we couldn't find the region you were looking for.</p>
        </article>
    </div>
{/if}
