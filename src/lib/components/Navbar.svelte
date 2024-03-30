<script lang="ts">
  import { getNumberOfAdventures } from "../../services/adventureService";
</script>
<div class="navbar bg-base-100">
    <div class="navbar-start">
        <button class="btn btn-primary mr-4 ml-2" on:click={() => window.location.href = '/'}>Home</button>
        <button class="btn btn-primary" on:click={() => window.location.href = '/log'}>My Log</button>
    </div>
    <div class="navbar-center">
      <a class="btn btn-ghost text-xl" href="/">AdventureLog 🗺️</a>
    </div>
    <div class="navbar-end">
      <p>Adventures: {getNumberOfAdventures()} </p>
      <button class="btn btn-ghost btn-circle">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
      </button>
      
      <button class="btn btn-ghost btn-circle">
        <div class="indicator">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" /></svg>
          <span class="badge badge-xs badge-primary indicator-item"></span>
          
        </div>
      </button>
    </div>
  </div>
