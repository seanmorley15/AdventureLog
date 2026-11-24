<script setup lang="ts">
import {
  SHOT_SIZE,
  shotFallback,
  shotSrcset,
  shots,
  type ShotName,
} from "../../screenshots";

/**
 * A real app screenshot in both app themes. Only the one matching the docs
 * theme is displayed, and both are lazy, so the hidden one is never fetched.
 */
const props = withDefaults(defineProps<{ name: ShotName; sizes?: string }>(), {
  sizes: "(min-width: 1200px) 1100px, 94vw",
});
const themes = ["light", "dark"] as const;
</script>

<template>
  <span class="al-shot">
    <picture
      v-for="theme in themes"
      :key="theme"
      :class="`al-shot__img al-shot__img--${theme}`"
    >
      <source
        type="image/avif"
        :srcset="shotSrcset(props.name, theme, 'avif')"
        :sizes="props.sizes"
      />
      <source
        type="image/webp"
        :srcset="shotSrcset(props.name, theme, 'webp')"
        :sizes="props.sizes"
      />
      <img
        :src="shotFallback(props.name, theme)"
        :alt="shots[props.name]"
        :width="SHOT_SIZE.width"
        :height="SHOT_SIZE.height"
        loading="lazy"
        decoding="async"
      />
    </picture>
  </span>
</template>
