<script setup lang="ts">
import AppShot from "./AppShot.vue";

const HALF = "(min-width: 1200px) 540px, (min-width: 760px) 46vw, 94vw";
</script>

<template>
  <div class="al-story">
    <section
      id="remember"
      class="al-chapter"
      aria-labelledby="remember-heading"
    >
      <header class="al-chapter__head">
        <p class="al-chapter__kicker">Travel log</p>
        <h2 id="remember-heading">Remember where you've been</h2>
        <p>
          A pin on a map forgets most of the trip. In AdventureLog every
          location keeps its own page: the photos you took, what you thought of
          it, when you were there, and the trail you walked to reach it.
        </p>
      </header>

      <figure class="al-figure al-figure--wide">
        <AppShot name="place" />
        <figcaption>
          A location page: photos, a rating, visits with dates, tags, and a
          linked hiking trail.
        </figcaption>
      </figure>

      <div class="al-pair">
        <figure class="al-figure">
          <AppShot name="world" :sizes="HALF" />
          <figcaption>
            <h3>Countries, regions, and cities</h3>
            <p>
              Mark where you've been and watch the world fill in, country by
              country and region by region.
            </p>
          </figcaption>
        </figure>
        <figure class="al-figure">
          <AppShot name="dashboard" :sizes="HALF" />
          <figcaption>
            <h3>Your travel so far</h3>
            <p>
              The dashboard keeps count of countries, locations, and trips, and
              shows the trip you're on right now.
            </p>
          </figcaption>
        </figure>
      </div>
    </section>

    <section id="plan" class="al-chapter" aria-labelledby="plan-heading">
      <header class="al-chapter__head">
        <p class="al-chapter__kicker">Trip planner</p>
        <h2 id="plan-heading">Plan where you're going next</h2>
        <p>
          Start with a list of ideas and turn it into an itinerary, day by day.
          Flights, trains, places to stay, notes, and packing lists sit in the
          order you'll need them, next to a map of the route.
        </p>
      </header>

      <figure class="al-figure al-figure--wide">
        <AppShot name="trip" />
        <figcaption>
          A trip planned day by day, with transport, stops, and lodging beside
          the route.
        </figcaption>
      </figure>

      <div class="al-pair">
        <figure class="al-figure">
          <AppShot name="collections" :sizes="HALF" />
          <figcaption>
            <h3>Trips and wish lists</h3>
            <p>
              Keep dated trips next to open-ended collections, like a bucket
              list or the national parks you still want to see.
            </p>
          </figcaption>
        </figure>
        <figure class="al-figure">
          <AppShot name="calendar" :sizes="HALF" />
          <figcaption>
            <h3>The whole trip on a calendar</h3>
            <p>
              See stops, transport, and lodging laid out by day, and download
              the calendar for the calendar app you already use.
            </p>
          </figcaption>
        </figure>
      </div>

      <p class="al-chapter__note">
        Planning with other people? Share a trip so your travel companions can
        edit it with you, or send a link to anyone who just needs to follow
        along.
      </p>
    </section>

    <section
      id="map"
      class="al-chapter al-chapter--map"
      aria-labelledby="map-heading"
    >
      <header class="al-chapter__head">
        <p class="al-chapter__kicker">World map</p>
        <h2 id="map-heading">See all of it on one map</h2>
        <p>
          The places you've been and the ones you're planning share a single
          interactive map. Filter by category, switch visited and planned on or
          off, and overlay the regions you've covered.
        </p>
      </header>
      <figure class="al-figure al-figure--wide">
        <AppShot name="map" />
        <figcaption>
          Every location across your trips on one map, grouped as you zoom out.
        </figcaption>
      </figure>
    </section>
  </div>
</template>
