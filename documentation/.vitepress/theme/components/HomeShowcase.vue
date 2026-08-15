<script setup lang="ts">
import { ref } from "vue";

const SHOT =
  "https://raw.githubusercontent.com/seanmorley15/AdventureLog/refs/heads/main/brand/screenshots";

const tabs = [
  {
    id: "locations",
    label: "Locations",
    title: "Every place, fully logged",
    desc: "Filter by visited or planned, sort by date or category, and keep rich notes, photos, and ratings for every stop on your journey.",
    src: `${SHOT}/adventures.png`,
    alt: "AdventureLog location list with filters and categories",
  },
  {
    id: "map",
    label: "World Map",
    title: "See your story on the map",
    desc: "Drop pins from the interactive MapLibre world map. Toggle visited vs planned and watch your travel history come alive.",
    src: `${SHOT}/map.png`,
    alt: "AdventureLog interactive world map with location pins",
  },
  {
    id: "itinerary",
    label: "Trip Planning",
    title: "Plan trips that actually happen",
    desc: "Build multi-day itineraries with flights, lodging, checklists, notes, and collaborative collections your whole group can edit.",
    src: `${SHOT}/itinerary.png`,
    alt: "AdventureLog trip itinerary planner with daily activities",
  },
  {
    id: "dashboard",
    label: "Dashboard",
    title: "Stats that celebrate travel",
    desc: "Track countries, regions, and cities visited. Your personal travel dashboard turns milestones into motivation.",
    src: `${SHOT}/dashboard.png`,
    alt: "AdventureLog travel statistics dashboard",
  },
  {
    id: "world",
    label: "World Travel",
    title: "Countries & regions explorer",
    desc: "Mark countries and regions as visited with interactive maps. Perfect for seeing your travel history.",
    src: `${SHOT}/countries.png`,
    alt: "AdventureLog countries and regions visited tracker",
  },
] as const;

const active = ref<(typeof tabs)[number]["id"]>("locations");
const current = () => tabs.find((t) => t.id === active.value) ?? tabs[0];
</script>

<template>
  <section class="al-showcase" aria-labelledby="showcase-heading">
    <div class="al-section-head al-section-head--center">
      <p class="al-eyebrow">See it in action</p>
      <h2 id="showcase-heading">Built for travelers who want more than a pin on a map</h2>
      <p class="al-section-lead">
        Track locations, plan itineraries, explore the world, and share trips —
        all in one self-hosted app you control.
      </p>
    </div>

    <div class="al-showcase__tabs" role="tablist" aria-label="Feature screenshots">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        type="button"
        role="tab"
        class="al-showcase__tab"
        :class="{ 'is-active': active === tab.id }"
        :aria-selected="active === tab.id"
        @click="active = tab.id"
      >
        {{ tab.label }}
      </button>
    </div>

    <div class="al-showcase__panel" role="tabpanel">
      <div class="al-showcase__text">
        <h3>{{ current().title }}</h3>
        <p>{{ current().desc }}</p>
      </div>
      <figure class="al-showcase__frame">
        <img
          :key="current().src"
          :src="current().src"
          :alt="current().alt"
          width="1280"
          height="720"
          loading="lazy"
          decoding="async"
        />
      </figure>
    </div>
  </section>
</template>
