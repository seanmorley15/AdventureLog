import { defineConfig } from "vitepress";
import { buildPageHead, pageSeo } from "./seo";

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
  description:
    "Self-hosted, open-source travel companion for tracking locations, planning trips, and sharing adventures.",
  lang: "en-US",

  sitemap: {
    hostname: "https://adventurelog.app",
  },

  rewrites: {
    "docs/Guides/nginx_migration.md": "docs/guides/v0-7-1_migration.md",
  },

  transformPageData(pageData) {
    const seo =
      pageSeo[pageData.relativePath] ??
      ({
        description:
          "AdventureLog documentation for self-hosted travel tracking, trip planning, and Docker deployment.",
      } as const);

    const pageTitle = seo.title ?? pageData.title;
    const head = buildPageHead(pageData.relativePath, pageTitle, seo);

    if (pageData.relativePath === "index.md") {
      const siteUrl = "https://adventurelog.app";
      const screenshot =
        "https://raw.githubusercontent.com/seanmorley15/AdventureLog/refs/heads/main/brand/screenshots/adventures.png";

      const structuredData = [
        {
          "@context": "https://schema.org",
          "@type": "WebSite",
          name: "AdventureLog",
          url: siteUrl,
          description: seo.description,
          inLanguage: "en-US",
          publisher: {
            "@type": "Organization",
            name: "AdventureLog",
            url: siteUrl,
            logo: `${siteUrl}/adventurelog.png`,
            sameAs: [
              "https://github.com/seanmorley15/AdventureLog",
              "https://discord.gg/wRbQ9Egr8C",
              "https://x.com/AdventureLogApp",
              "https://mastodon.social/@adventurelog",
            ],
          },
        },
        {
          "@context": "https://schema.org",
          "@type": "SoftwareApplication",
          name: "AdventureLog",
          url: siteUrl,
          applicationCategory: "TravelApplication",
          operatingSystem: "Web, Docker, Linux, macOS",
          description: seo.description,
          featureList: [
            "Location and visit tracking",
            "Interactive world map",
            "Trip itineraries and collections",
            "World travel country and region tracker",
            "Strava, Immich, and Wanderer integrations",
            "Self-hosted Docker deployment",
          ],
          creator: {
            "@type": "Person",
            name: "Sean Morley",
            url: "https://seanmorley.com",
          },
          offers: {
            "@type": "Offer",
            price: "0",
            priceCurrency: "USD",
            description: "Free open-source self-hosted travel companion.",
          },
          softwareVersion: "v0.12.1",
          license:
            "https://github.com/seanmorley15/adventurelog/blob/main/LICENSE",
          screenshot,
          downloadUrl: "https://github.com/seanmorley15/adventurelog",
          installUrl: `${siteUrl}/docs/install/quick_start.html`,
          sameAs: ["https://github.com/seanmorley15/adventurelog"],
          keywords: (seo.keywords ?? []).join(", "),
        },
        {
          "@context": "https://schema.org",
          "@type": "FAQPage",
          mainEntity: [
            {
              "@type": "Question",
              name: "What is AdventureLog?",
              acceptedAnswer: {
                "@type": "Answer",
                text: "AdventureLog is an open-source, self-hosted travel companion for tracking locations, planning trips with itineraries, and visualizing travels on an interactive world map.",
              },
            },
            {
              "@type": "Question",
              name: "How do I install AdventureLog?",
              acceptedAnswer: {
                "@type": "Answer",
                text: "Run curl -sSL https://get.adventurelog.app | bash to install with the official one-line Docker installer. It defaults to the All-in-One setup on port 8015.",
              },
            },
            {
              "@type": "Question",
              name: "Is AdventureLog free?",
              acceptedAnswer: {
                "@type": "Answer",
                text: "Yes. AdventureLog is GPL-3.0 open source and free to self-host. There are no subscriptions required for the self-hosted version.",
              },
            },
            {
              "@type": "Question",
              name: "Can I self-host AdventureLog on a homelab or NAS?",
              acceptedAnswer: {
                "@type": "Answer",
                text: "Yes. AdventureLog runs in Docker on homelabs, VPS, Proxmox, Synology NAS, Unraid, Kubernetes, and other Docker-capable platforms.",
              },
            },
          ],
        },
      ];

      for (const graph of structuredData) {
        head.push([
          "script",
          { type: "application/ld+json" },
          JSON.stringify(graph),
        ]);
      }
    }

    const description =
      pageData.frontmatter.description ?? seo.description ?? pageData.description;

    return {
      title: seo.title ?? pageData.title,
      description,
      frontmatter: {
        ...pageData.frontmatter,
        description,
        head: [...(pageData.frontmatter.head ?? []), ...head],
      },
    };
  },

  themeConfig: {
    nav: [
      { text: "Home", link: "/" },
      { text: "Install", link: "/docs/install/getting_started" },
      { text: "Configure", link: "/docs/configuration/environment_variables" },
      { text: "Usage", link: "/docs/usage/usage" },
      {
        text: "GitHub",
        link: "https://github.com/seanmorley15/AdventureLog",
      },
    ],
    search: {
      provider: "local",
    },
    editLink: {
      pattern:
        "https://github.com/seanmorley15/AdventureLog/edit/main/documentation/:path",
    },

    footer: {
      message: "AdventureLog — self-hosted travel companion",
      copyright: "Copyright © 2023-2026 Sean Morley",
    },

    logo: "/adventurelog.png",

    sidebar: [
      {
        text: "Introduction",
        items: [
          {
            text: "About AdventureLog",
            link: "/docs/intro/adventurelog_overview",
          },
        ],
      },
      {
        text: "Installation",
        collapsed: false,
        items: [
          { text: "Getting Started", link: "/docs/install/getting_started" },
          { text: "Quick Start Installer", link: "/docs/install/quick_start" },
          { text: "All-in-One Docker (AIO)", link: "/docs/install/aio" },
          { text: "Standard Docker", link: "/docs/install/docker" },
          {
            text: "Development Setup",
            link: "/docs/install/dev_container_wsl",
          },
          {
            text: "Platform Guides",
            collapsed: true,
            items: [
              { text: "Proxmox LXC", link: "/docs/install/proxmox_lxc" },
              { text: "Synology NAS", link: "/docs/install/synology_nas" },
              { text: "Unraid", link: "/docs/install/unraid" },
              {
                text: "Kubernetes (Kustomize)",
                link: "/docs/install/kustomize",
              },
            ],
          },
          {
            text: "Reverse Proxy",
            collapsed: true,
            items: [
              {
                text: "Nginx Proxy Manager",
                link: "/docs/install/nginx_proxy_manager",
              },
              { text: "Traefik", link: "/docs/install/traefik" },
              { text: "Caddy", link: "/docs/install/caddy" },
            ],
          },
        ],
      },
      {
        text: "Usage",
        collapsed: false,
        items: [
          { text: "How to Use AdventureLog", link: "/docs/usage/usage" },
        ],
      },
      {
        text: "Configuration",
        collapsed: false,
        items: [
          {
            text: "Environment Variables",
            link: "/docs/configuration/environment_variables",
          },
          {
            text: "Operations & Maintenance",
            link: "/docs/configuration/operations",
          },
          { text: "Updating", link: "/docs/configuration/updating" },
          {
            text: "Authentication",
            collapsed: true,
            items: [
              {
                text: "Social Auth & OIDC",
                link: "/docs/configuration/social_auth",
              },
              {
                text: "Authentik",
                link: "/docs/configuration/social_auth/authentik",
              },
              {
                text: "GitHub",
                link: "/docs/configuration/social_auth/github",
              },
              {
                text: "Pocket ID",
                link: "/docs/configuration/social_auth/pocket_id",
              },
              {
                text: "OpenID Connect",
                link: "/docs/configuration/social_auth/oidc",
              },
              {
                text: "Authelia",
                link: "https://www.authelia.com/integration/openid-connect/adventure-log/",
              },
              {
                text: "Disable Registration",
                link: "/docs/configuration/disable_registration",
              },
              { text: "API Keys", link: "/docs/configuration/api_keys" },
            ],
          },
          {
            text: "Integrations",
            collapsed: true,
            items: [
              {
                text: "Immich",
                link: "/docs/configuration/immich_integration",
              },
              {
                text: "Google Maps",
                link: "/docs/configuration/google_maps_integration",
              },
              {
                text: "Strava",
                link: "/docs/configuration/strava_integration",
              },
              {
                text: "Wanderer",
                link: "/docs/configuration/wanderer_integration",
              },
            ],
          },
          {
            text: "Storage & Email",
            collapsed: true,
            items: [
              { text: "S3 Media Storage", link: "/docs/configuration/s3_storage" },
              { text: "SMTP Email", link: "/docs/configuration/email" },
            ],
          },
          {
            text: "Advanced Settings",
            link: "/docs/configuration/advanced_configuration",
          },
          { text: "Umami Analytics", link: "/docs/configuration/analytics" },
        ],
      },
      {
        text: "Troubleshooting",
        collapsed: true,
        items: [
          {
            text: "Images Not Displaying",
            link: "/docs/troubleshooting/no_images",
          },
          {
            text: "Login Unresponsive",
            link: "/docs/troubleshooting/login_unresponsive",
          },
          {
            text: "Nginx Failed to Start",
            link: "/docs/troubleshooting/nginx_failed",
          },
        ],
      },
      {
        text: "Guides",
        collapsed: true,
        items: [
          { text: "Admin Panel", link: "/docs/guides/admin_panel" },
          { text: "Invite a User", link: "/docs/guides/invite_user" },
          {
            text: "v0.7.1 Migration",
            link: "/docs/guides/v0-7-1_migration",
          },
        ],
      },
      {
        text: "Changelogs",
        collapsed: true,
        items: [
          {
            text: "Development Timeline",
            link: "/docs/changelogs/development_timeline",
          },
          { text: "v0.12.1", link: "/docs/changelogs/v0-12-1" },
          { text: "v0.12.0", link: "/docs/changelogs/v0-12-0" },
          { text: "v0.11.0", link: "/docs/changelogs/v0-11-0" },
          { text: "v0.10.0", link: "/docs/changelogs/v0-10-0" },
          { text: "v0.9.0", link: "/docs/changelogs/v0-9-0" },
          { text: "v0.8.0", link: "/docs/changelogs/v0-8-0" },
          { text: "v0.7.1", link: "/docs/changelogs/v0-7-1" },
          { text: "v0.7.0", link: "/docs/changelogs/v0-7-0" },
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
