<!-- routes/signup/+page.svelte -->
<script lang="ts">
  import { enhance } from "$app/forms";
  import { goto } from "$app/navigation";
  import { getRandomQuote } from "$lib";
  import type { SubmitFunction } from "@sveltejs/kit";
  import { onMount } from "svelte";

  export let data;

  let errors: { message?: string } = {};
  let backgroundImageUrl = "https://source.unsplash.com/random/?mountains";

  let quote: string = "";
  onMount(async () => {
    quote = getRandomQuote();
  });

  const handleSubmit: SubmitFunction = async ({ formData, action, cancel }) => {
    const response = await fetch(action, {
      method: "POST",
      body: formData,
    });

    if (response.ok) {
      errors = {};
      goto("/signup");
      return;
    }

    const { type, error } = await response.json();
    if (type === "error") {
      errors = { message: error.message };
    }
    console.log(errors);
    cancel();
  };
</script>

<div
  class="min-h-screen bg-no-repeat bg-cover flex items-center justify-center"
  style="background-image: url('{data.image}')"
>
  <div class="card card-compact w-96 bg-base-100 shadow-xl p-6 mt-4 mb-4">
    <article class="text-center text-4xl font-extrabold">
      <h1>Signup</h1>
    </article>

    <div class="flex justify-center">
      <form method="post" use:enhance={handleSubmit} class="w-full max-w-xs">
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
        /><br /><label for="password">Confirm Password</label>
        <input
          type="password"
          name="passwordConfirm"
          id="passwordConfirm"
          class="block mb-2 input input-bordered w-full max-w-xs"
        /><br />
        <button class="py-2 px-4 btn btn-primary">Signup</button>
      </form>
    </div>

    {#if errors.message}
      <div class="text-center text-error mt-4">
        {errors.message}
      </div>
    {/if}

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
