<script lang="ts">
    import { goto } from '$app/navigation';
    import campingDrawing from "$lib/assets/camping.svg";
    async function navToLog() {
        goto('/log');
    }
</script>

<div class="flex flex-col items-center justify-center">
    <article class="prose"><h1 class="mb-4">Welcome. Let's get Exploring!</h1></article>
    <img src={campingDrawing} class="w-1/4 mb-4" alt="Logo" />
    <button on:click={navToLog} class="btn btn-primary">Open Log</button>
</div>