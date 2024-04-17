<!-- routes/login/+page.svelte -->
<script lang="ts">
  import { enhance } from "$app/forms";
  import { goto } from "$app/navigation";
  import { getRandomQuote } from "$lib";
  import { redirect, type SubmitFunction } from "@sveltejs/kit";
  import { onMount } from "svelte";
  let quote: string = "";
  let errors: { message?: string } = {};
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
      goto("/login");
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

<article class="text-center text-4xl font-extrabold">
  <h1>Sign in</h1>
</article>

<div class="flex justify-center">
  <form method="post" use:enhance={handleSubmit} class="w-full max-w-xs">
    <label for="username">Username</label>
    <input
      name="username"
      id="username"
      class="block mb-2 input input-bordered w-full max-w-xs"
    /><br />
    <label for="password">Password</label>
    <input
      type="password"
      name="password"
      id="password"
      class="block mb-2 input input-bordered w-full max-w-xs"
    /><br />
    <button class="py-2 px-4 btn btn-primary">Login</button>
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
