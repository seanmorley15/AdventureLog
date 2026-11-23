<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from "vue";
import AppShot from "./AppShot.vue";
import type { ShotName } from "../../screenshots";

type View = { shot: ShotName; title: string; text: string };
type Chapter = {
  id: string;
  tab: string;
  kicker: string;
  title: string;
  intro: string;
  views: View[];
  note?: string;
};

// One showcase instead of three stacked chapters: every screenshot and
// sentence is still here, but only one view takes up the screen at a time.
const chapters: Chapter[] = [
  {
    id: "remember",
    tab: "Remember",
    kicker: "Travel log",
    title: "Remember where you've been",
    intro:
      "A pin on a map forgets most of the trip. In AdventureLog every location keeps its own page: the photos you took, what you thought of it, when you were there, and the trail you walked to reach it.",
    views: [
      {
        shot: "place",
        title: "A page for every location",
        text: "Photos, a rating, visits with dates, tags, and a linked hiking trail.",
      },
      {
        shot: "world",
        title: "Countries, regions, and cities",
        text: "Mark where you've been and watch the world fill in, country by country and region by region.",
      },
      {
        shot: "dashboard",
        title: "Your travel so far",
        text: "The dashboard keeps count of countries, locations, and trips, and shows the trip you're on right now.",
      },
    ],
  },
  {
    id: "plan",
    tab: "Plan",
    kicker: "Trip planner",
    title: "Plan where you're going next",
    intro:
      "Start with a list of ideas and turn it into an itinerary, day by day. Flights, trains, places to stay, notes, and packing lists sit in the order you'll need them, next to a map of the route.",
    views: [
      {
        shot: "trip",
        title: "Day-by-day itineraries",
        text: "Transport, stops, and lodging beside the route.",
      },
      {
        shot: "collections",
        title: "Trips and wish lists",
        text: "Keep dated trips next to open-ended collections, like a bucket list or the national parks you still want to see.",
      },
      {
        shot: "calendar",
        title: "The whole trip on a calendar",
        text: "See stops, transport, and lodging laid out by day, and download the calendar for the calendar app you already use.",
      },
    ],
    note: "Planning with other people? Share a trip so your travel companions can edit it with you, or send a link to anyone who just needs to follow along.",
  },
  {
    id: "map",
    tab: "Map",
    kicker: "World map",
    title: "See all of it on one map",
    intro:
      "The places you've been and the ones you're planning share a single interactive map. Filter by category, switch visited and planned on or off, and overlay the regions you've covered.",
    views: [
      {
        shot: "map",
        title: "Everything on one map",
        text: "Every location across your trips, grouped as you zoom out.",
      },
    ],
  },
];

const chapterIndex = ref(0);
const viewIndex = ref<number[]>(chapters.map(() => 0));
// Screenshots are only added to the page once someone looks at them.
const seen = ref(new Set<string>([`${chapters[0].id}:0`]));

const chapter = computed(() => chapters[chapterIndex.value]);

function markSeen(c: number, v: number) {
  seen.value = new Set(seen.value).add(`${chapters[c].id}:${v}`);
}

function selectChapter(i: number) {
  chapterIndex.value = i;
  markSeen(i, viewIndex.value[i]);
}

function selectView(v: number) {
  viewIndex.value[chapterIndex.value] = v;
  markSeen(chapterIndex.value, v);
}

function onTabKey(e: KeyboardEvent) {
  const last = chapters.length - 1;
  let next = chapterIndex.value;
  if (e.key === "ArrowRight") next = next === last ? 0 : next + 1;
  else if (e.key === "ArrowLeft") next = next === 0 ? last : next - 1;
  else if (e.key === "Home") next = 0;
  else if (e.key === "End") next = last;
  else return;
  e.preventDefault();
  selectChapter(next);
  nextTick(() =>
    document.getElementById(`showcase-tab-${chapters[next].id}`)?.focus(),
  );
}

// Old links to /#remember, /#plan and /#map open the matching tab.
function openFromHash() {
  const i = chapters.findIndex((c) => `#${c.id}` === location.hash);
  if (i < 0) return;
  selectChapter(i);
  nextTick(() =>
    document
      .getElementById("showcase")
      ?.scrollIntoView({ behavior: "auto", block: "start" }),
  );
}

onMounted(() => {
  openFromHash();
  window.addEventListener("hashchange", openFromHash);
});
</script>

<template>
  <div class="al-story">
    <section id="showcase" class="al-showcase" aria-label="What AdventureLog does">
      <div class="al-showcase__tabs" role="tablist" aria-label="Features">
        <button
          v-for="(c, i) in chapters"
          :id="`showcase-tab-${c.id}`"
          :key="c.id"
          type="button"
          role="tab"
          class="al-showcase__tab"
          :aria-selected="i === chapterIndex"
          :aria-controls="`showcase-panel-${c.id}`"
          :tabindex="i === chapterIndex ? 0 : -1"
          @click="selectChapter(i)"
          @keydown="onTabKey"
        >
          <span class="al-showcase__tab-kicker">{{ c.kicker }}</span>
          <span class="al-showcase__tab-label">{{ c.tab }}</span>
        </button>
      </div>

      <!-- Every panel stays in the HTML (hidden), so the copy is always indexable. -->
      <div
        v-for="(c, ci) in chapters"
        :id="`showcase-panel-${c.id}`"
        :key="c.id"
        class="al-showcase__panel"
        role="tabpanel"
        :aria-labelledby="`showcase-tab-${c.id}`"
        :hidden="ci !== chapterIndex"
      >
        <div class="al-showcase__copy">
          <h2 :id="`${c.id}-heading`">{{ c.title }}</h2>
          <p class="al-showcase__intro">{{ c.intro }}</p>

          <ul v-if="c.views.length > 1" class="al-showcase__views">
            <li v-for="(v, vi) in c.views" :key="v.shot">
              <button
                type="button"
                class="al-showcase__view"
                :aria-pressed="vi === viewIndex[ci]"
                @click="selectView(vi)"
              >
                <strong>{{ v.title }}</strong>
                <span>{{ v.text }}</span>
              </button>
            </li>
          </ul>
          <p v-else class="al-showcase__single">{{ c.views[0].text }}</p>

          <p v-if="c.note" class="al-showcase__note">{{ c.note }}</p>
        </div>

        <div class="al-showcase__stage">
          <figure
            v-for="(v, vi) in c.views"
            :key="v.shot"
            class="al-showcase__shot"
            :class="{ 'is-active': vi === viewIndex[ci] }"
          >
            <AppShot
              v-if="seen.has(`${c.id}:${vi}`)"
              :name="v.shot"
              sizes="(min-width: 1200px) 720px, (min-width: 900px) 60vw, 94vw"
            />
            <figcaption class="al-visually-hidden">{{ v.title }}. {{ v.text }}</figcaption>
          </figure>
        </div>
      </div>
    </section>
  </div>
</template>
