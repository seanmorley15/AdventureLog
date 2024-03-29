<style>
    .navbar {
        display: flex;
        justify-content: center;
        align-items: center;
        flex-direction: row;
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

    <p>AdventureLog 🗺️</p>
    <button on:click={navHome}>Home</button>
    <button on:click={navLog}>Log</button>
    <hr>
    <br>
</div>
