<script setup lang="ts">
const SHOT =
  "https://raw.githubusercontent.com/seanmorley15/AdventureLog/refs/heads/main/brand/screenshots";

const badges = ["Self-hosted", "Open source", "GPL-3.0", "Docker-ready"];

function scrollToContent(event: Event) {
  event.preventDefault();
  const target = document.getElementById("showcase-heading");
  if (!target) return;

  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  target.scrollIntoView({
    behavior: prefersReducedMotion ? "auto" : "smooth",
    block: "start",
  });
}
</script>

<template>
  <section class="al-hero" aria-labelledby="hero-heading">
    <div class="al-hero__backdrop" aria-hidden="true">
      <div class="al-hero__grid" />
      <div class="al-hero__orb al-hero__orb--green" />
      <div class="al-hero__orb al-hero__orb--blue" />
      <div class="al-hero__orb al-hero__orb--violet" />
    </div>

    <div class="al-hero__inner">
      <div class="al-hero__copy">
        <p class="al-hero__pill">
          <span class="al-hero__pill-dot" aria-hidden="true" />
          The ultimate travel companion
        </p>

        <h1 id="hero-heading" class="al-hero__title">
          Everything travel,
          <span class="al-hero__title-accent">united in one place.</span>
        </h1>

        <p class="al-hero__lead">
          Log every place you've been, plan what's ahead, and watch your whole
          travel story unfold on one beautiful map — on your server, on your terms.
        </p>

        <div class="al-hero__actions">
          <a class="al-hero__btn al-hero__btn--primary" href="/docs/install/getting_started">
            Get started
            <svg width="18" height="18" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path
                d="M3 8h10M9 4l4 4-4 4"
                stroke="currentColor"
                stroke-width="1.75"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
          </a>
          <a
            class="al-hero__btn al-hero__btn--secondary"
            href="https://demo.adventurelog.app"
            target="_blank"
            rel="noopener noreferrer"
          >
            Live demo
          </a>
        </div>

        <ul class="al-hero__badges" aria-label="Highlights">
          <li v-for="badge in badges" :key="badge">{{ badge }}</li>
        </ul>
      </div>

      <div class="al-hero__visual">
        <div class="al-hero__glow" aria-hidden="true" />
        <div class="al-hero__frame">
          <div class="al-hero__chrome" aria-hidden="true">
            <span /><span /><span />
            <div class="al-hero__url">adventurelog.app</div>
          </div>
          <img
            class="al-hero__shot"
            :src="`${SHOT}/adventures.png`"
            alt="AdventureLog location list with map, visit filters, and trip categories"
            width="1200"
            height="675"
            loading="eager"
            fetchpriority="high"
            decoding="async"
          />
        </div>

        <div class="al-hero__float al-hero__float--map" aria-hidden="true">
          <span class="al-hero__float-icon">🗺️</span>
          <div>
            <strong>World map</strong>
            <small>Pin &amp; filter locations</small>
          </div>
        </div>
        <div class="al-hero__float al-hero__float--docker" aria-hidden="true">
          <span class="al-hero__float-icon">✈️</span>
          <div>
            <strong>Trip planning</strong>
            <small>Itineraries &amp; checklists</small>
          </div>
        </div>
      </div>
    </div>

    <a
      href="#showcase-heading"
      class="al-hero__scroll"
      aria-label="Scroll to explore features"
      @click="scrollToContent"
    >
      <span class="al-hero__scroll-label">Explore</span>
      <span class="al-hero__scroll-icon" aria-hidden="true">
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <path
            d="M5 8l5 5 5-5"
            stroke="currentColor"
            stroke-width="1.75"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
      </span>
    </a>
  </section>
</template>
