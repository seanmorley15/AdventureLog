<script setup lang="ts">
import { faq } from "../../faq";
</script>

<template>
  <section class="al-faq" aria-labelledby="faq-heading">
    <div class="al-section-head al-section-head--center">
      <h2 id="faq-heading">Questions people ask first</h2>
    </div>

    <div class="al-faq__list">
      <details v-for="item in faq" :key="item.question" class="al-faq__item">
        <summary>
          <h3>{{ item.question }}</h3>
          <svg
            width="18"
            height="18"
            viewBox="0 0 20 20"
            fill="none"
            aria-hidden="true"
          >
            <path
              d="M5 8l5 5 5-5"
              stroke="currentColor"
              stroke-width="1.75"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </svg>
        </summary>
        <div class="al-faq__answer">
          <p>{{ item.answer }}</p>
          <p v-if="item.links?.length" class="al-faq__links">
            <a v-for="link in item.links" :key="link.href" :href="link.href">{{
              link.text
            }}</a>
          </p>
        </div>
      </details>
    </div>
  </section>
</template>
