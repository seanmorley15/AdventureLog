<script lang="ts">
    import { createEventDispatcher } from 'svelte';
    const dispatch = createEventDispatcher();

    export let name:String;
    export let location:String;
    export let created:string;
    export let id:Number;

    function remove() {
        dispatch('remove', id);
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