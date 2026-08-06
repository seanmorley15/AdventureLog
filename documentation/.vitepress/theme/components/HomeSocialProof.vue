<script setup lang="ts">
const quotes = [
  {
    quote:
      "It's an open-source, self-hosted travel planner that's completely free to use… Safe to say, it's become a mainstay in Docker for me.",
    author: "Sumukh Rao",
    role: "Senior Author, XDA",
    rank: null,
    href: "https://www.xda-developers.com/i-self-hosted-this-app-to-plan-itinerary-when-traveling/",
  },
  {
    quote:
      "AdventureLog is aptly named… one of the best apps for the job and can be fully self-hosted at home.",
    author: "Rich Edmonds",
    role: "Lead PC Hardware Editor, XDA",
    rank: "#1 self-hosted travel app",
    href: "https://www.xda-developers.com/these-self-hosted-apps-are-perfect-for-those-on-the-go/",
  },
  {
    quote:
      "AdventureLog represents a new era of travel tracking: open, private, comprehensive, and truly yours.",
    author: "Open Source Daily",
    role: "Publication",
    rank: null,
    href: "https://opensourcedaily.blog/adventurelog-private-open-source-travel-tracking-trip-planning/",
  },
  {
    quote:
      "AdventureLog behaves more like a super-charged travel journal than yet another travel app.",
    author: "Dhruv Bhutani",
    role: "Android Authority",
    rank: null,
    href: "https://www.androidauthority.com/self-hosted-travel-app-3572353/",
  },
];
</script>

<template>
  <section class="al-proof" aria-labelledby="proof-heading">
    <div class="al-section-head al-section-head--center">
      <p class="al-eyebrow">Trusted by the self-hosting community</p>
      <h2 id="proof-heading">Featured in XDA, Android Authority &amp; more</h2>
    </div>
    <div class="al-proof__grid">
      <blockquote v-for="q in quotes" :key="q.href" class="al-quote">
        <p>"{{ q.quote }}"</p>
        <footer>
          <cite>{{ q.author }}</cite>
          <span>{{ q.role }}</span>
          <span v-if="q.rank" class="al-quote__rank">{{ q.rank }}</span>
        </footer>
        <a :href="q.href" target="_blank" rel="noopener noreferrer">Read article →</a>
      </blockquote>
    </div>
  </section>
</template>
