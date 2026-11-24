<script setup lang="ts">
const links = [
  { text: "Install AdventureLog", href: "/docs/install/getting_started" },
  {
    text: "Environment variables",
    href: "/docs/configuration/environment_variables",
  },
  { text: "How to use AdventureLog", href: "/docs/usage/usage" },
  { text: "Troubleshooting", href: "/docs/troubleshooting/login_unresponsive" },
  { text: "Changelogs", href: "/docs/changelogs/development_timeline" },
];
</script>

<template>
  <section class="al-404" aria-labelledby="not-found-heading">
    <p class="al-404__code">404</p>
    <h1 id="not-found-heading">This page isn't on the map</h1>
    <p class="al-404__lead">
      The link may be old, or the page moved. Use search at the top of the page,
      or pick up from one of these.
    </p>
    <ul class="al-404__links">
      <li v-for="link in links" :key="link.href">
        <a :href="link.href">{{ link.text }}</a>
      </li>
    </ul>
    <a class="al-404__home" href="/">Back to the homepage</a>
  </section>
</template>
