<script setup lang="ts">
/**
 * A thin strip above the nav announcing the latest release. The version comes
 * from GitHub at build time, so it updates on the next deploy after a release.
 * It shows for a week after the release; dismissing it hides it until the next
 * version. config.mts adds the `al-announce` class before first paint (and
 * checks the date in the browser), so the page never jumps.
 */
import { data as repo } from "../../github.data";

// Link to our own changelog page when it exists, otherwise to GitHub.
const pages = import.meta.glob("../../../docs/changelogs/*.md");
const slug = repo.version?.replace(/\./g, "-");
const local =
  slug && Object.keys(pages).some((path) => path.endsWith(`/${slug}.md`));
const href = local ? `/docs/changelogs/${slug}` : repo.releaseUrl;

function dismiss() {
  document.documentElement.classList.remove("al-announce");
  try {
    localStorage.setItem("al-announce-dismissed", repo.version ?? "");
  } catch {
    // Private mode: it stays dismissed for this page view only.
  }
}
</script>

<template>
  <aside
    v-if="repo.announce && href"
    class="al-announce-bar"
    aria-label="Latest release"
  >
    <p>
      <span class="al-announce-bar__long">AdventureLog </span
      >{{ repo.version }} is out.
      <a
        :href="href"
        :target="local ? undefined : '_blank'"
        :rel="local ? undefined : 'noopener noreferrer'"
      >
        <span class="al-announce-bar__long">Read the </span>release notes
      </a>
    </p>
    <button type="button" aria-label="Dismiss announcement" @click="dismiss">
      <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">
        <path
          d="M2 2l10 10M12 2L2 12"
          stroke="currentColor"
          stroke-width="1.75"
          stroke-linecap="round"
        />
      </svg>
    </button>
  </aside>
</template>
