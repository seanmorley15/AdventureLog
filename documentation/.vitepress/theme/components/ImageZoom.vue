<script setup lang="ts">
/**
 * Click a screenshot or docs image to see it full size. One listener on the
 * page handles every image, including ones added by navigation. Images that
 * are links, icons, or the logo are left alone.
 */
import { nextTick, onBeforeUnmount, onMounted, ref } from "vue";

const dialog = ref<HTMLDialogElement | null>(null);
const src = ref("");
const alt = ref("");

function target(event: Event): HTMLImageElement | null {
  const el = event.target;
  if (!(el instanceof HTMLImageElement)) return null;
  if (
    !el.closest(".vp-doc, .al-hero__app") ||
    el.closest("a, .al-hero__scene, .al-final")
  )
    return null;
  if (el.naturalWidth < 400) return null;
  return el;
}

function open(event: MouseEvent) {
  const img = target(event);
  if (!img || event.defaultPrevented) return;
  // App screenshots have a larger encoded size than the one on the page.
  src.value = (img.currentSrc || img.src).replace(
    /-(800|1440)\.(avif|webp)$/,
    "-2200.$2",
  );
  alt.value = img.alt;
  nextTick(() => dialog.value?.showModal());
}

function close() {
  dialog.value?.close();
}

onMounted(() => document.addEventListener("click", open));
onBeforeUnmount(() => document.removeEventListener("click", open));
</script>

<template>
  <dialog
    ref="dialog"
    class="al-zoom"
    aria-label="Enlarged image"
    @click="close"
    @close="src = ''"
  >
    <img v-if="src" :src="src" :alt="alt" />
    <button type="button" class="al-zoom__close" aria-label="Close">
      <svg width="16" height="16" viewBox="0 0 14 14" aria-hidden="true">
        <path
          d="M2 2l10 10M12 2L2 12"
          stroke="currentColor"
          stroke-width="1.75"
          stroke-linecap="round"
        />
      </svg>
    </button>
  </dialog>
</template>
