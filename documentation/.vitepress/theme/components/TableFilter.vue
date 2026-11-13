<script setup lang="ts">
/**
 * A filter box for reference pages made of markdown tables. The tables stay
 * plain markdown (so search, the outline, and no-JS readers all still work);
 * this only hides rows that don't match, and sections with no rows left.
 */
import { nextTick, onMounted, ref, watch } from "vue";

const props = withDefaults(defineProps<{ label?: string; noun?: string }>(), {
  label: "Filter variables",
  noun: "variables",
});

const query = ref("");
const total = ref(0);
const shown = ref(0);
const root = ref<HTMLElement | null>(null);

type Section = {
  heading: HTMLElement | null;
  between: HTMLElement[];
  table: HTMLElement;
  rows: HTMLElement[];
};
let sections: Section[] = [];

function collect() {
  sections = [];
  const tables: HTMLElement[] = [];
  // Every table after this component in the page.
  for (
    let el = root.value?.nextElementSibling;
    el;
    el = el.nextElementSibling
  ) {
    if (el instanceof HTMLTableElement) tables.push(el);
  }
  for (const table of tables) {
    const between: HTMLElement[] = [];
    let heading: HTMLElement | null = null;
    for (
      let el = table.previousElementSibling;
      el;
      el = el.previousElementSibling
    ) {
      if (/^H[2-4]$/.test(el.tagName)) {
        heading = el as HTMLElement;
        break;
      }
      if (el instanceof HTMLTableElement || el === root.value) break;
      between.push(el as HTMLElement);
    }
    sections.push({
      heading,
      between,
      table,
      rows: [...table.querySelectorAll<HTMLElement>("tbody tr")],
    });
  }
  total.value = sections.reduce((n, s) => n + s.rows.length, 0);
  shown.value = total.value;
}

function apply() {
  const words = query.value.toLowerCase().split(/\s+/).filter(Boolean);
  let count = 0;
  const liveHeadings = new Set<HTMLElement>();
  for (const section of sections) {
    let hits = 0;
    for (const row of section.rows) {
      const text = row.textContent?.toLowerCase() ?? "";
      const match = words.every((w) => text.includes(w));
      row.hidden = !match;
      if (match) hits++;
    }
    count += hits;
    section.table.hidden = hits === 0;
    for (const el of section.between)
      el.hidden = hits === 0 && words.length > 0;
    if (hits > 0 && section.heading) liveHeadings.add(section.heading);
  }
  for (const section of sections) {
    if (section.heading)
      section.heading.hidden =
        words.length > 0 && !liveHeadings.has(section.heading);
  }
  shown.value = count;
}

onMounted(() => nextTick(collect));
watch(query, apply);
</script>

<template>
  <div ref="root" class="al-filter">
    <label class="al-filter__field">
      <span class="visually-hidden">{{ props.label }}</span>
      <svg
        width="16"
        height="16"
        viewBox="0 0 16 16"
        fill="none"
        aria-hidden="true"
      >
        <circle
          cx="7"
          cy="7"
          r="4.5"
          stroke="currentColor"
          stroke-width="1.5"
        />
        <path
          d="M10.5 10.5L14 14"
          stroke="currentColor"
          stroke-width="1.5"
          stroke-linecap="round"
        />
      </svg>
      <input
        v-model="query"
        type="search"
        :placeholder="props.label"
        autocomplete="off"
        spellcheck="false"
      />
    </label>
    <p class="al-filter__count" aria-live="polite">
      <template v-if="!query">{{ total }} {{ props.noun }}</template>
      <template v-else-if="shown"
        >{{ shown }} of {{ total }} {{ props.noun }}</template
      >
      <template v-else>No {{ props.noun }} match "{{ query }}".</template>
    </p>
  </div>
</template>
