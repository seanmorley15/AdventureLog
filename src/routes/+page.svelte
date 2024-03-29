<script lang="ts">
    import campingDrawing from "$lib/assets/camping.svg";
    function navToLog() {
        window.location.href = '/log';
    }
</script>

<h1>Welcome to AdventureLog 🗺️</h1>
<img src={campingDrawing} width="25%" alt="Logo" />
<button on:click={navToLog}>Open Log</button>

<style>
    button {
        margin-left: 1rem;
        padding: 0.5rem 1rem;
        border: none;
        border-radius: 4px;
        background-color: #076836;
        color: white;
        cursor: pointer;
        transition: background-color 0.3s ease;
        box-shadow: 0px 2px 5px rgba(0,0,0,0.1);
        margin-left: auto;
        margin-right: auto;
        display: block;
    }

    button:hover {
        background-color: #074b28;
    }
    h1 {
        text-align: center;
    }
    img {
        display: block;
        margin-left: auto;
        margin-right: auto;
        margin-top: 2rem;
        margin-bottom: 2rem;
    }
</style>