<style>
    .navbar {
        display: flex;
        justify-content: center;
        align-items: center;
        flex-direction: row;
    }

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
    }

    button:hover {
        background-color: #074b28;
    }
</style>

<script lang="ts">
    function navHome() {
        window.location.href = '/';
    
    }
    function navLog() {
        window.location.href = '/log';
    }
</script>


<div class="navbar">

    <h2>AdventureLog 🗺️</h2>
    <button on:click={navHome}>Home</button>
    <button on:click={navLog}>Log</button>
    <hr>
    <br>
</div>
