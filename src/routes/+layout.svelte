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
  }

  let isServerSetup = data.isServerSetup;

  onMount(() => {
    console.log("isServerSetup", isServerSetup);
    if (!isServerSetup && $page.url.pathname !== "/setup") {
      goto("/setup");
    }
    if (isServerSetup && $page.url.pathname == "/setup") {
      goto("/");
    }
  });
</script>

<!-- passes the user object to the navbar component -->
<Navbar user={data.user} />
<section>
  <slot />
</section>
<!-- <Footer /> -->

<!-- <style>
    section {
        margin-top: 2rem;
        margin-bottom: 5rem;
        /* gives the footer space! */
    }
  </style> -->
