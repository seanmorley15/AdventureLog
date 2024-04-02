<script lang="ts">
    import { createEventDispatcher } from 'svelte';
    import locationDot from "$lib/assets/locationDot.svg";
    import calendar from "$lib/assets/calendar.svg";
    const dispatch = createEventDispatcher();

    export let name:String;
    export let location:String;

    function add() {
        dispatch('add', {name, location});
    }
</script>

<div class="card min-w-max lg:w-96 md:w-80 sm:w-60 xs:w-40 bg-neutral shadow-xl overflow-hidden">
    <div class="card-body">
      <h2 class="card-title overflow-ellipsis">{name}</h2>
      <p><img src={locationDot} class="inline-block -mt-1 mr-1" alt="Logo" />{location}</p>
      <div class="card-actions justify-end">
        <button class="btn btn-primary" on:click={add}>Add</button>
      </div>
    </div>
</div>

