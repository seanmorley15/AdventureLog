<script setup lang="ts">
import AppShot from "./AppShot.vue";
import MountainScene from "./MountainScene.vue";
</script>

<template>
  <section class="al-hero" aria-labelledby="hero-heading">
    <div class="al-hero__scene">
      <MountainScene />

      <div class="al-hero__copy">
        <h1 id="hero-heading" class="al-hero__title">
          Everything travel, united in one place.
        </h1>
        <p class="al-hero__lead">
          AdventureLog is your ultimate travel journal and trip planner. Track
          the places you've visited, organize your discoveries, and plan what's
          next.
        </p>
        <div class="al-hero__actions">
          <a
            class="al-button al-button--brand"
            href="/docs/install/getting_started"
          >
            Get started
          </a>
          <a
            class="al-button al-button--outline"
            href="https://demo.adventurelog.app"
            target="_blank"
            rel="noopener noreferrer"
          >
            Try the demo
          </a>
        </div>
      </div>
    </div>

    <figure class="al-hero__app">
      <AppShot name="locations" />
      <figcaption>
        Your locations in AdventureLog, each with its photos, notes, rating, and
        visits.
      </figcaption>
    </figure>
  </section>
</template>
