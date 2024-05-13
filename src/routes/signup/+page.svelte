<!-- routes/signup/+page.svelte -->
<script lang="ts">
  import { enhance } from "$app/forms";
  import { getRandomQuote } from "$lib";
  import { onMount } from "svelte";

  let backgroundImageUrl = "https://source.unsplash.com/random/?mountains";

  let quote: string = "";
  onMount(async () => {
    quote = getRandomQuote();
  });
</script>

<div
  class="min-h-screen bg-no-repeat bg-cover flex items-center justify-center"
  style="background-image: url('{backgroundImageUrl}')"
>
  <div class="card card-compact w-96 bg-base-100 shadow-xl p-6">
    <article class="text-center text-4xl font-extrabold">
      <h1>Signup</h1>
    </article>

    <div class="flex justify-center">
      <form method="post" use:enhance class="w-full max-w-xs">
        <label for="username">Username</label>
        <input
          name="username"
          id="username"
          class="block mb-2 input input-bordered w-full max-w-xs"
        /><br />
        <label for="first_name">First Name</label>
        <input
          name="first_name"
          id="first_name"
          class="block mb-2 input input-bordered w-full max-w-xs"
        /><br />
        <label for="last_name">Last Name</label>
        <input
          name="last_name"
          id="last_name"
          class="block mb-2 input input-bordered w-full max-w-xs"
        /><br />
        <label for="password">Password</label>
        <input
          type="password"
          name="password"
          id="password"
          class="block mb-2 input input-bordered w-full max-w-xs"
        /><br />
        <button class="py-2 px-4 btn btn-primary">Signup</button>
      </form>
    </div>

    <div class="flex justify-center mt-12 mr-25 ml-25">
      <blockquote class="w-80 text-center text-lg break-words">
        {#if quote != ""}
          {quote}
        {/if}
        <!-- <footer class="text-sm">- Steve Jobs</footer> -->
      </blockquote>
    </div>
  </div>
</div>

<!-- username first last pass -->

<svelte:head>
  <title>Signup | AdventureLog</title>
  <meta
    name="description"
    content="Signup for AdventureLog to start logging your adventures!"
  />
</svelte:head>
