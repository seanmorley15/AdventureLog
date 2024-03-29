<script lang="ts">
    import { createEventDispatcher } from 'svelte';
    const dispatch = createEventDispatcher();

    export let name:String;
    export let location:String;
    export let created:string;
    export let id:Number;

    function remove() {
        dispatch('remove', name);
    }
    function edit() {
        dispatch('edit', id)
    }
</script>

<div>
    <!-- <p>ID: {id}</p> -->
    <p>Name: {name}</p>
    <p>Location: {location}</p>
    <p>Created: {created}</p>
    <button on:click={remove}>Remove</button>
    <button on:click={edit}>Edit</button>
</div>

<style>
    div {
        margin: 2rem;
        padding: .5rem;
        background-color: rgb(235, 230, 223);
        border: 1px solid grey;
        border-radius: .5rem;
        box-shadow: 10px 5px 5px rgba(0, 0, 0, 0.182);
    }
</style>