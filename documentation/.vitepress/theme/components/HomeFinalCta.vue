<script setup lang="ts">
import { photos, photoSrcset } from "../../screenshots";

const photo = photos.philmont;
</script>

<template>
  <section class="al-final" aria-labelledby="final-heading">
    <picture>
      <source
        type="image/avif"
        :srcset="photoSrcset('philmont', 'avif')"
        sizes="100vw"
      />
      <source
        type="image/webp"
        :srcset="photoSrcset('philmont', 'webp')"
        sizes="100vw"
      />
      <img
        class="al-final__photo"
        src="/photos/philmont-1600.webp"
        :alt="photo.alt"
        :width="photo.width"
        :height="photo.height"
        loading="lazy"
        decoding="async"
      />
    </picture>
    <div class="al-final__inner">
      <h2 id="final-heading">
        Your next adventure deserves more than a camera roll
      </h2>
      <p>
        Look around the demo, or have your own instance running in a few
        minutes.
      </p>
      <div class="al-final__actions">
        <a
          class="al-button al-button--light"
          href="https://demo.adventurelog.app"
          target="_blank"
          rel="noopener noreferrer"
        >
          Try the live demo
        </a>
        <a
          class="al-button al-button--outline-light"
          href="/docs/install/standard"
        >
          Install AdventureLog
        </a>
        <a class="al-button al-button--outline-light" href="/docs/usage/usage">
          Read the guide
        </a>
      </div>
      <p class="al-final__support">
        <a
          href="https://discord.gg/wRbQ9Egr8C"
          target="_blank"
          rel="noopener noreferrer"
          >Discord</a
        >
        <a
          href="https://github.com/seanmorley15/AdventureLog"
          target="_blank"
          rel="noopener noreferrer"
          >GitHub</a
        >
        <a
          href="https://github.com/seanmorley15/AdventureLog/issues"
          target="_blank"
          rel="noopener noreferrer"
          >Report an issue</a
        >
      </p>
    </div>
    <p class="al-final__credit">{{ photo.place }}. Photo by Sean Morley.</p>
  </section>
</template>
