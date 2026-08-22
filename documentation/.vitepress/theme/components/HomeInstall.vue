<script setup lang="ts">
type InstallPath = {
  icon: string;
  title: string;
  desc: string;
  href: string;
  external?: boolean;
  featured?: boolean;
};

type InstallPathGroup = {
  id: string;
  label: string;
  icon: string;
  paths: InstallPath[];
};

const pathGroups: InstallPathGroup[] = [
  {
    id: "docker",
    label: "Docker",
    icon: "🐳",
    paths: [
      {
        icon: "📦",
        title: "Standard Deployment",
        desc: "Default for most installs — one container, one port.",
        href: "/docs/install/standard",
        featured: true,
      },
      {
        icon: "⚡",
        title: "Quick Start Installer",
        desc: "Guided walkthrough that deploys Standard Deployment for you.",
        href: "/docs/install/quick_start",
      },
      {
        icon: "🐋",
        title: "Advanced Deployment",
        desc: "Frontend, backend, and PostGIS — full control.",
        href: "/docs/install/docker",
      },
    ],
  },
  {
    id: "homelab",
    label: "Homelab & NAS",
    icon: "🏠",
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
        icon: "🔌",
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
    id: "kubernetes",
    label: "Kubernetes",
    icon: "☸️",
    paths: [
      {
        icon: "🌐",
        title: "Kubernetes + Kustomize",
        desc: "Deploy with manifests in k8s/base/.",
        href: "/docs/install/kustomize",
      },
    ],
  },
];
</script>

<template>
  <section class="al-install" aria-labelledby="install-heading">
    <div class="al-install__inner">
      <header class="al-install__head al-section-head al-section-head--center">
        <p class="al-eyebrow">Installation</p>
        <h2 id="install-heading">Choose how you run AdventureLog</h2>
        <p class="al-install__lead">
          Most people run Standard Deployment — one container on a single port.
          Platform guides and Kubernetes are there when you need them.
        </p>
      </header>

      <div class="al-install__shell">
        <div class="al-install__bento">
          <article
            v-for="group in pathGroups"
            :key="group.id"
            class="al-install__category"
            :class="`al-install__category--${group.id}`"
          >
            <header class="al-install__category-head">
              <span class="al-install__category-icon" aria-hidden="true">{{ group.icon }}</span>
              <h3>{{ group.label }}</h3>
            </header>

            <ul class="al-install__menu">
              <li v-for="path in group.paths" :key="path.href">
                <a
                  class="al-install__menu-link"
                  :href="path.href"
                  :target="path.external ? '_blank' : undefined"
                  :rel="path.external ? 'noopener noreferrer' : undefined"
                >
                  <span class="al-install__menu-icon" aria-hidden="true">{{ path.icon }}</span>
                  <span class="al-install__menu-text">
                    <strong>
                      {{ path.title }}
                      <span v-if="path.featured" class="al-install__menu-tag">Popular</span>
                    </strong>
                    <small>{{ path.desc }}</small>
                  </span>
                  <span class="al-install__menu-arrow" aria-hidden="true">
                    {{ path.external ? "↗" : "→" }}
                  </span>
                </a>
              </li>
            </ul>
          </article>
        </div>

        <footer class="al-install__foot">
          <a class="al-btn al-btn--brand" href="/docs/install/getting_started">
            All install options
          </a>
          <a class="al-install__foot-link" href="/docs/install/traefik">
            Reverse proxy with Traefik
            <span aria-hidden="true">→</span>
          </a>
        </footer>
      </div>
    </div>
  </section>
</template>
