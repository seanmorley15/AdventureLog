<script lang="ts">
    import { createEventDispatcher } from 'svelte';
    import locationDot from "$lib/assets/locationDot.svg";
    import calendar from "$lib/assets/calendar.svg";
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

<div class="card min-w-max w-96 bg-neutral shadow-xl overflow-hidden">
    <div class="card-body">
      <h2 class="card-title overflow-ellipsis">{name}</h2>
      <p><img src={locationDot} class="inline-block -mt-1 mr-1" alt="Logo" />{location}</p>
      <p><img src={calendar} class="inline-block -mt-1 mr-1" alt="Logo" />{created}</p>
      <div class="card-actions justify-end">
        <button class="btn btn-primary" on:click={edit}>Edit</button>
        <button class="btn btn-secondary" on:click={remove}>Remove</button>
      </div>
    </div>
</div>

