<script lang="ts">
  import Footer from "$lib/components/Footer.svelte";
  import Navbar from "$lib/components/Navbar.svelte";
  import "../app.css";

  // only show footer if scrolled to the bottom
</script>

<Navbar />
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
