<script lang="ts">
  export let data;
  import Footer from "$lib/components/Footer.svelte";
  import Navbar from "$lib/components/Navbar.svelte";
  import type { SubmitFunction } from "@sveltejs/kit";
  import "../app.css";
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
