<script setup lang="ts">
const points = [
  {
    title: "Your data stays with you",
    text: "AdventureLog runs on your own server, from a homelab or NAS to a small VPS. Back up or export everything whenever you like.",
    link: { text: "Install options", href: "/docs/install/getting_started" },
  },
  {
    title: "Works with what you already use",
    text: "Bring in photos from Immich, activities from Strava and Endurain, trails from Wanderer, and place search from Google Maps.",
    link: {
      text: "Immich integration",
      href: "/docs/configuration/immich_integration",
    },
  },
  {
    title: "Sign in your way",
    text: "Use local accounts with two-factor authentication, or connect an OpenID Connect provider such as Authentik, Authelia, or Pocket ID.",
    link: {
      text: "Social auth and OIDC",
      href: "/docs/configuration/social_auth",
    },
  },
  {
    title: "Free and open source",
    text: "Released under GPL-3.0 and built in the open. Read the code, script it through the API, or help shape what comes next.",
    link: { text: "API keys", href: "/docs/configuration/api_keys" },
  },
];
</script>

<template>
  <section class="al-pillars" aria-labelledby="pillars-heading">
    <header class="al-chapter__head">
      <p class="al-chapter__kicker">Self-hosted</p>
      <h2 id="pillars-heading">Open source, on your own server</h2>
      <p>
        Your travel history is personal. AdventureLog keeps it on hardware you
        control, with no subscription and no feature limits.
      </p>
    </header>
    <div class="al-pillars__grid">
      <article v-for="p in points" :key="p.title" class="al-pillar">
        <h3>{{ p.title }}</h3>
        <p>{{ p.text }}</p>
        <a :href="p.link.href">{{ p.link.text }}</a>
      </article>
    </div>
  </section>
</template>
