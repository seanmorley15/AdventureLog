<script setup lang="ts">
const links = [
  { label: "GitHub", href: "https://github.com/seanmorley15/AdventureLog" },
  { label: "Discord", href: "https://discord.gg/wRbQ9Egr8C" },
  { label: "Live demo", href: "https://demo.adventurelog.app", external: true },
  { label: "Documentation", href: "/docs/intro/adventurelog_overview" },
];
</script>

<template>
  <footer class="al-site-footer">
    <div class="al-site-footer__inner">
      <div class="al-site-footer__brand">
        <a class="al-site-footer__logo" href="/" aria-label="AdventureLog home">
          <img src="/adventurelog.png" alt="" width="32" height="32" />
          <span>AdventureLog</span>
        </a>
        <p class="al-site-footer__tagline">The ultimate travel companion</p>
      </div>

      <nav class="al-site-footer__nav" aria-label="Footer">
        <a
          v-for="link in links"
          :key="link.href"
          :href="link.href"
          :target="link.external ? '_blank' : undefined"
          :rel="link.external ? 'noopener noreferrer' : undefined"
        >
          {{ link.label }}
        </a>
      </nav>

      <p class="al-site-footer__copy">
        © 2023–2026 Sean Morley · Open source under
        <a
          href="https://github.com/seanmorley15/AdventureLog/blob/main/LICENSE"
          target="_blank"
          rel="noopener noreferrer"
        >GPL-3.0</a>
      </p>
    </div>
  </footer>
</template>
