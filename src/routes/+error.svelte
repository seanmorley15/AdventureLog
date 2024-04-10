<script>
    // @ts-nocheck

    import { page } from "$app/stores";
    import { goto } from "$app/navigation";

    async function goHome() {
        goto("/");
    }
</script>

<article class="text-center font-extrabold text-4xl mt-16">
    <h1>{$page.error.message}</h1>
</article>

<div class="flex justify-center items-center">
    <button class="btn btn-primary" on:click={goHome}>Go Home</button>
</div>
