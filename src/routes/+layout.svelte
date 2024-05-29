<script lang="ts">
  export let data;
  import Footer from "$lib/components/Footer.svelte";
  import Navbar from "$lib/components/Navbar.svelte";
  import type { SubmitFunction } from "@sveltejs/kit";
  import "../app.css";
  import { goto } from "$app/navigation";
  import { onMount } from "svelte";
  import { page } from "$app/stores";
  import { inject } from "@vercel/analytics";
  import { injectSpeedInsights } from "@vercel/speed-insights/sveltekit";
  import "iconify-icon";

  if (data.usingVercel === "true") {
    inject();
    injectSpeedInsights();
  } else {
    // console.log("Not using Vercel");
  }

  let isServerSetup = data.isServerSetup;

  onMount(() => {
    if (!isServerSetup && $page.url.pathname !== "/setup") {
      goto("/setup");
    }
    if (isServerSetup && $page.url.pathname == "/setup") {
      goto("/");
    }
  });
</script>

<div class="flex flex-col min-h-screen">
  <!-- passes the user object to the navbar component -->
  <Navbar user={data.user} />
  <main class="flex-grow">
    <slot />
  </main>
  <Footer />
</div>
