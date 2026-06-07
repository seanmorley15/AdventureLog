<script setup lang="ts">
const features = [
  {
    icon: "📍",
    title: "Log locations & visits",
    summary: "More than a pin on a map — a real record of each place.",
    details:
      "Add dates, notes, photos, trails, and categories. Mark spots as visited or planned, attach Strava activities, and browse everything on an interactive world map.",
  },
  {
    icon: "✈️",
    title: "Plan trips & itineraries",
    summary: "Collections that grow into full travel plans.",
    details:
      "Organize multi-day trips with flights, lodging, transport, daily notes, and packing checklists. Share collections and plan together with the people you travel with.",
  },
  {
    icon: "🌍",
    title: "Track your world travel",
    summary: "See how far you've gone — and what's still on the list.",
    details:
      "Mark countries, regions, and cities as visited. View travel stats on your dashboard and explore your progress with maps built for bucket lists and lifetime goals.",
  },
];
</script>

<template>
  <section class="al-features" aria-labelledby="features-heading">
    <div class="al-features__inner">
      <header class="al-features__head">
        <p class="al-eyebrow">What you can do</p>
        <h2 id="features-heading">Log, plan, and explore — in one travel app</h2>
        <p class="al-features__lead">
          From weekend getaways to years of backpacking, AdventureLog keeps your
          past trips memorable and your next ones organized.
        </p>
      </header>

      <div class="al-features__grid">
        <article v-for="(f, i) in features" :key="f.title" class="al-features__card">
          <span class="al-features__step" aria-hidden="true">{{ i + 1 }}</span>
          <div class="al-features__icon" aria-hidden="true">{{ f.icon }}</div>
          <h3>{{ f.title }}</h3>
          <p class="al-features__summary">{{ f.summary }}</p>
          <p class="al-features__details">{{ f.details }}</p>
        </article>
      </div>
    </div>
  </section>
</template>
