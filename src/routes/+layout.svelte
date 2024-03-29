<script>
    import Footer from "$lib/components/Footer.svelte";
</script>

<section>
    <slot></slot>
  </section>
  <Footer />

  <style>
    section {
        margin-bottom: 5rem;
        /* gives the footer space! */
    }
  </style>