<script lang="ts">
    export let data;
</script>

{#each data.regions as region}
    <p>{region.name}</p>
{/each}
