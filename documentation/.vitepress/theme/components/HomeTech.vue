<script setup lang="ts">
const stacks = [
  {
    title: "Frontend",
    items: ["SvelteKit", "TailwindCSS", "DaisyUI", "MapLibre GL"],
  },
  {
    title: "Backend",
    items: ["Django", "Django REST", "PostGIS", "django-allauth"],
  },
  {
    title: "Deploy",
    items: ["Docker Compose", "Kubernetes", "GHCR images", "One-line installer"],
  },
];
</script>

<template>
  <section class="al-tech" aria-labelledby="tech-heading">
    <div class="al-section-head al-section-head--center">
      <p class="al-eyebrow">Modern stack</p>
      <h2 id="tech-heading">Built with tools you already trust</h2>
    </div>
    <div class="al-tech__grid">
      <div v-for="stack in stacks" :key="stack.title" class="al-tech__card">
        <h3>{{ stack.title }}</h3>
        <ul>
          <li v-for="item in stack.items" :key="item">{{ item }}</li>
        </ul>
      </div>
    </div>
  </section>
</template>
