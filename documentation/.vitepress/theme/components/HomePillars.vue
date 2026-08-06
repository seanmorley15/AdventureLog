<script setup lang="ts">
const pillars = [
  {
    icon: "📋",
    title: "Rich location logs",
    text: "Photos, attachments, ratings, tags, and visit history — everything you need to remember why a place mattered.",
  },
  {
    icon: "🗺️",
    title: "Interactive maps",
    text: "Drop pins from the world map, filter visited vs planned, and see your trips take shape visually.",
  },
  {
    icon: "📅",
    title: "Full itineraries",
    text: "Flights, lodging, transport, notes, and checklists organized by day for trips that are easy to follow.",
  },
  {
    icon: "🌐",
    title: "World travel book",
    text: "Track countries, regions, and cities you've explored — with maps and stats that show your progress.",
  },
  {
    icon: "📊",
    title: "Travel dashboard",
    text: "Countries visited, regions explored, and milestones at a glance — celebrate how much of the world you've seen.",
  },
  {
    icon: "📸",
    title: "Integrations",
    text: "Pull in photos from Immich, activities from Strava, trails from Wanderer, and places from Google Maps.",
  },
];
</script>

<template>
  <section class="al-pillars" aria-labelledby="pillars-heading">
    <div class="al-section-head al-section-head--center">
      <p class="al-eyebrow">Go deeper</p>
      <h2 id="pillars-heading">Features built for real travelers</h2>
      <p class="al-section-lead al-pillars__lead">
        Whether you're planning a road trip or logging years of adventures,
        AdventureLog has the tools to capture the full picture.
      </p>
    </div>
    <div class="al-pillars__grid">
      <article v-for="p in pillars" :key="p.title" class="al-pillar">
        <span class="al-pillar__icon" aria-hidden="true">{{ p.icon }}</span>
        <h3>{{ p.title }}</h3>
        <p>{{ p.text }}</p>
      </article>
    </div>
  </section>
</template>
