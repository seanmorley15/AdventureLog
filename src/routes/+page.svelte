<script lang="ts">
    import campingDrawing from "$lib/assets/camping.svg";
    function navToLog() {
        window.location.href = '/log';
    }
</script>

<h1>Welcome to AdventureLog 🗺️</h1>
<img src={campingDrawing} width="25%" alt="Logo" />
<button on:click={navToLog}>Open Log</button>
