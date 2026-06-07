<script setup lang="ts">
import { ref } from "vue";

const SHOT =
  "https://raw.githubusercontent.com/seanmorley15/AdventureLog/refs/heads/main/brand/screenshots";

const command = "curl -sSL https://get.adventurelog.app | bash";
const copied = ref(false);

async function copy() {
  try {
    await navigator.clipboard.writeText(command);
    copied.value = true;
    setTimeout(() => (copied.value = false), 2000);
  } catch {
    /* clipboard unavailable */
  }
}
</script>

<template>
  <section class="al-hero" aria-labelledby="hero-heading">
    <div class="al-hero__backdrop" aria-hidden="true">
      <div class="al-hero__grid" />
      <div class="al-hero__orb al-hero__orb--green" />
      <div class="al-hero__orb al-hero__orb--blue" />
    </div>

    <div class="al-hero__inner">
      <div class="al-hero__copy">
        <p class="al-hero__pill">
          <span class="al-hero__pill-dot" aria-hidden="true" />
          Locations · Itineraries · World map
        </p>

        <h1 id="hero-heading" class="al-hero__title">
          Everything travel,
          <span class="al-hero__title-accent">united in one place.</span>
        </h1>

        <p class="al-hero__lead">
          Remember where you've been, plan what's ahead, and see your whole
          travel story on one map.
        </p>

        <div class="al-hero__actions">
          <a class="al-hero__btn al-hero__btn--primary" href="/docs/install/getting_started">
            Get started
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
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

        <div class="al-hero__install-block">
          <p class="al-hero__install-label">
            All-in-One Docker
            <span class="al-hero__install-sep" aria-hidden="true">·</span>
            <a href="/docs/install/aio">manual setup</a>
          </p>
          <div class="al-hero__install">
            <code class="al-hero__cmd">
              <span class="al-hero__prompt" aria-hidden="true">$</span>
              {{ command }}
            </code>
            <button
              type="button"
              class="al-hero__copy-btn"
              :aria-label="copied ? 'Copied' : 'Copy guided installer command'"
              @click="copy"
            >
              {{ copied ? "Copied" : "Copy" }}
            </button>
          </div>
          <p class="al-hero__install-note">
            Guided installer — deploys AIO by default.
            <a href="/docs/install/quick_start">Details</a>
          </p>
        </div>

        <ul class="al-hero__stats" aria-label="Core features">
          <li><strong>Locations</strong> visits, photos &amp; trails</li>
          <li><strong>Itineraries</strong> flights, lodging &amp; notes</li>
          <li><strong>World travel</strong> countries &amp; regions</li>
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
  </section>
</template>
