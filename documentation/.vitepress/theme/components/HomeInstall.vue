<script setup lang="ts">
import { ref } from "vue";

const command = "curl -sSL https://get.adventurelog.app | bash";
const copied = ref(false);

type InstallPath = {
  icon: string;
  title: string;
  desc: string;
  href: string;
  external?: boolean;
};

type InstallPathGroup = {
  label: string;
  paths: InstallPath[];
};

const pathGroups: InstallPathGroup[] = [
  {
    label: "Docker",
    paths: [
      {
        icon: "⚡",
        title: "Quick Start Installer",
        desc: "Guided one-line install — AIO by default.",
        href: "/docs/install/quick_start",
      },
      {
        icon: "📦",
        title: "All-in-One Docker",
        desc: "Single container, one port, minimal config.",
        href: "/docs/install/aio",
      },
      {
        icon: "🐋",
        title: "Standard Docker",
        desc: "Frontend, backend, and PostGIS — full control.",
        href: "/docs/install/docker",
      },
    ],
  },
  {
    label: "Homelab & NAS",
    paths: [
      {
        icon: "🐧",
        title: "Proxmox LXC",
        desc: "Lightweight LXC container with Docker.",
        href: "/docs/install/proxmox_lxc",
      },
      {
        icon: "☁️",
        title: "Synology NAS",
        desc: "Install via Container Manager on Synology.",
        href: "/docs/install/synology_nas",
      },
      {
        icon: "🧡",
        title: "Unraid",
        desc: "Docker templates for Unraid homelabs.",
        href: "/docs/install/unraid",
      },
      {
        icon: "🏠",
        title: "Umbrel",
        desc: "Community app for Umbrel home servers.",
        href: "https://apps.umbrel.com/app/adventurelog",
        external: true,
      },
      {
        icon: "💾",
        title: "TrueNAS",
        desc: "Community app catalog for TrueNAS SCALE.",
        href: "https://apps.truenas.com/catalog/adventurelog/",
        external: true,
      },
    ],
  },
  {
    label: "Kubernetes",
    paths: [
      {
        icon: "🌐",
        title: "Kubernetes + Kustomize",
        desc: "Deploy with manifests in `k8s/base/`.",
        href: "/docs/install/kustomize",
      },
    ],
  },
];

async function copy() {
  try {
    await navigator.clipboard.writeText(command);
    copied.value = true;
    setTimeout(() => (copied.value = false), 2000);
  } catch {
    /* clipboard unavailable */
  }
}
</script>

<template>
  <section class="al-install" aria-labelledby="install-heading">
    <div class="al-install__inner">
      <div class="al-install__copy">
        <p class="al-eyebrow">Installation</p>
        <h2 id="install-heading">Choose how you run AdventureLog</h2>
        <p class="al-install__desc">
          Docker guides for most setups, plus platform-specific instructions
          for Proxmox, Synology, Unraid, Umbrel, TrueNAS, and Kubernetes.
        </p>
        <ul class="al-install__badges" aria-label="Install methods">
          <li>Docker Compose</li>
          <li>Homelab &amp; NAS</li>
          <li>Kubernetes</li>
          <li>Reverse proxy</li>
        </ul>
        <div class="al-install__links">
          <a class="al-btn al-btn--brand" href="/docs/install/getting_started">
            All install options
          </a>
          <a class="al-btn al-btn--ghost" href="/docs/install/quick_start">
            Quick Start
          </a>
        </div>
      </div>

      <div class="al-install__panel">
        <p class="al-install__panel-label">Install paths</p>

        <div
          v-for="group in pathGroups"
          :key="group.label"
          class="al-install__group"
        >
          <p class="al-install__group-label">{{ group.label }}</p>
          <ul class="al-install__paths">
            <li v-for="path in group.paths" :key="path.href">
              <a
                class="al-install__path"
                :href="path.href"
                :target="path.external ? '_blank' : undefined"
                :rel="path.external ? 'noopener noreferrer' : undefined"
              >
                <span class="al-install__path-icon" aria-hidden="true">{{ path.icon }}</span>
                <span class="al-install__path-text">
                  <strong>{{ path.title }}</strong>
                  <small>{{ path.desc }}</small>
                </span>
                <span class="al-install__path-arrow" aria-hidden="true">→</span>
              </a>
            </li>
          </ul>
        </div>

        <div class="al-install__quick" role="group" aria-label="Quick Start command">
          <div class="al-install__quick-head">
            <span>Fastest path</span>
            <button
              type="button"
              class="al-install__quick-copy"
              :aria-label="copied ? 'Copied' : 'Copy install command'"
              @click="copy"
            >
              {{ copied ? "Copied" : "Copy" }}
            </button>
          </div>
          <code class="al-install__quick-cmd">
            <span class="al-prompt" aria-hidden="true">$</span> {{ command }}
          </code>
        </div>
      </div>
    </div>
  </section>
</template>
