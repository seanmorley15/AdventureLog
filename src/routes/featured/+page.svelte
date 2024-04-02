<script lang="ts">
    export let data
    console.log(data.result);
    import AdventureCard from '$lib/components/AdventureCard.svelte';
</script>

<div class="grid xl:grid-cols-3 lg:grid-cols-3 md:grid-cols-2 sm:grid-cols-1 gap-4 mt-4 content-center auto-cols-auto ml-6 mr-6">
    {#each data.result as adventure (adventure.id)}
        <AdventureCard id={adventure.id} name={adventure.name} location={adventure.location} created={adventure.created} />
    {/each}
</div>