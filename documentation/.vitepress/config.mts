import { defineConfig } from "vitepress";

// https://vitepress.dev/reference/site-config
export default defineConfig({
  head: [
    ["link", { rel: "icon", href: "/adventurelog.png" }],

    [
      "script",
      {
        defer: "",
        src: "https://cloud.umami.is/script.js",
        "data-website-id": "a7552764-5a1d-4fe7-80c2-5331e1a53cb6",
      },
    ],

    [
      "link",
      {
        rel: "me",
        href: "https://mastodon.social/@adventurelog",
      },
    ],
  ],
  ignoreDeadLinks: "localhostLinks",
  title: "AdventureLog",
  description: "The ultimate travel companion.",
  lang: "en-US",

  sitemap: {
    hostname: "https://adventurelog.app",
  },

  transformPageData(pageData) {
    if (pageData.relativePath === "index.md") {
      const jsonLd = {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        name: "AdventureLog",
        url: "https://adventurelog.app",
        applicationCategory: "TravelApplication",
        operatingSystem: "Web, Docker, Linux",
        description:
          "AdventureLog is a self-hosted platform for tracking and planning travel experiences. Built for modern explorers, it offers trip planning, journaling, tracking and location mapping in one privacy-respecting package.",
        creator: {
          "@type": "Person",
          name: "Sean Morley",
          url: "https://seanmorley.com",
        },
        offers: {
          "@type": "Offer",
          price: "0.00",
          priceCurrency: "USD",
          description: "Open-source version available for self-hosting.",
        },
        softwareVersion: "v0.10.0",
        license:
          "https://github.com/seanmorley15/adventurelog/blob/main/LICENSE",
        screenshot:
          "https://raw.githubusercontent.com/seanmorley15/AdventureLog/refs/heads/main/brand/screenshots/adventures.png",
        downloadUrl: "https://github.com/seanmorley15/adventurelog",
        sameAs: ["https://github.com/seanmorley15/adventurelog"],
        keywords: [
          "self-hosted travel log",
          "open source trip planner",
          "travel journaling app",
          "docker travel diary",
          "map-based travel tracker",
          "privacy-focused travel app",
          "adventure log software",
          "travel experience tracker",
          "self-hosted travel app",
          "open source travel software",
          "trip planning tool",
          "travel itinerary manager",
          "location-based travel app",
          "travel experience sharing",
          "travel log application",
        ],
      };

      return {
        frontmatter: {
          ...pageData.frontmatter,
          head: [
            ["script", { type: "application/ld+json" }, JSON.stringify(jsonLd)],
          ],
        },
      };
    }

    return {};
  },

  themeConfig: {
    // https://vitepress.dev/reference/default-theme-config
    nav: [
      { text: "Home", link: "/" },
      { text: "Docs", link: "/docs/intro/adventurelog_overview" },
    ],
    search: {
      provider: "local",
    },
    editLink: {
      pattern:
        "https://github.com/seanmorley15/AdventureLog/edit/main/documentation/:path",
    },

    footer: {
      message: "AdventureLog",
      copyright: "Copyright © 2023-2025 Sean Morley",
    },

    logo: "/adventurelog.png",

    sidebar: [
      {
        text: "About AdventureLog",
        items: [
          {
            text: "AdventureLog Overview",
            link: "/docs/intro/adventurelog_overview",
          },
        ],
      },

      {
        text: "Installation",
        collapsed: false,
        items: [
          { text: "Getting Started", link: "/docs/install/getting_started" },
          { text: "Quick Start Script ⏲️", link: "/docs/install/quick_start" },
          { text: "Docker 🐋", link: "/docs/install/docker" },
          { text: "Proxmox LXC 🐧", link: "/docs/install/proxmox_lxc" },
          { text: "Synology NAS ☁️", link: "/docs/install/synology_nas" },
          {
            text: "Kubernetes and Kustomize 🌐",
            link: "/docs/install/kustomize",
          },
          { text: "Unraid 🧡", link: "/docs/install/unraid" },

          {
            text: "With A Reverse Proxy",
            collapsed: false,
            items: [
              {
                text: "Nginx Proxy Manager",
                link: "/docs/install/nginx_proxy_manager",
              },
              { text: "Traefik", link: "/docs/install/traefik" },
              { text: "Caddy", link: "/docs/install/caddy" },
              { text: "HAProxy", link: "/docs/install/haproxy" },
            ],
          },
        ],
      },
      {
        text: "Usage",
        collapsed: false,
        items: [
          {
            text: "How to use AdventureLog",
            link: "/docs/usage/usage",
          },
        ],
      },
      {
        text: "Configuration",
        collapsed: false,
        items: [
          {
            text: "Immich Integration",
            link: "/docs/configuration/immich_integration",
          },
          {
            text: "Google Maps Integration",
            link: "/docs/configuration/google_maps_integration",
          },
          {
            text: "Social Auth and OIDC",
            link: "/docs/configuration/social_auth",
          },
          {
            text: "Authentication Providers",
            collapsed: false,
            items: [
              {
                text: "Authentik",
                link: "/docs/configuration/social_auth/authentik",
              },
              {
                text: "GitHub",
                link: "/docs/configuration/social_auth/github",
              },
              {
                text: "Authelia",
                link: "https://www.authelia.com/integration/openid-connect/adventure-log/",
              },
              {
                text: "Open ID Connect",
                link: "/docs/configuration/social_auth/oidc",
              },
            ],
          },
          {
            text: "Update App",
            link: "/docs/configuration/updating",
          },
          {
            text: "Disable Registration",
            link: "/docs/configuration/disable_registration",
          },
          { text: "SMTP Email", link: "/docs/configuration/email" },
          { text: "Umami Analytics", link: "/docs/configuration/analytics" },
        ],
      },
      {
        text: "Troubleshooting",
        collapsed: false,
        items: [
          {
            text: "No Images Displaying",
            link: "/docs/troubleshooting/no_images",
          },
          {
            text: "Login and Registration Unresponsive",
            link: "/docs/troubleshooting/login_unresponsive",
          },
          {
            text: "Failed to Start Nginx",
            link: "/docs/troubleshooting/nginx_failed",
          },
        ],
      },
      {
        text: "Guides",
        collapsed: false,
        items: [
          {
            text: "Admin Panel",
            link: "/docs/guides/admin_panel",
          },
          {
            text: "v0.7.1 Migration Guide",
            link: "/docs/guides/v0-7-1_migration",
          },
        ],
      },
      {
        text: "Changelogs",
        collapsed: false,
        items: [
          {
            text: "v0.10.0",
            link: "/docs/changelogs/v0-10-0",
          },
          {
            text: "v0.9.0",
            link: "/docs/changelogs/v0-9-0",
          },
          {
            text: "v0.8.0",
            link: "/docs/changelogs/v0-8-0",
          },
          {
            text: "v0.7.1",
            link: "/docs/changelogs/v0-7-1",
          },
          {
            text: "v0.7.0",
            link: "/docs/changelogs/v0-7-0",
          },
        ],
      },
    ],

    socialLinks: [
      { icon: "github", link: "https://github.com/seanmorley15/AdventureLog" },
      { icon: "discord", link: "https://discord.gg/wRbQ9Egr8C" },
      { icon: "buymeacoffee", link: "https://buymeacoffee.com/seanmorley15" },
      { icon: "x", link: "https://x.com/AdventureLogApp" },
      { icon: "mastodon", link: "https://mastodon.social/@adventurelog" },
      { icon: "instagram", link: "https://www.instagram.com/adventurelogapp" },
    ],
  },
});
