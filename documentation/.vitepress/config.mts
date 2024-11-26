import { defineConfig } from "vitepress";

// https://vitepress.dev/reference/site-config
export default defineConfig({
  head: [["link", { rel: "icon", href: "/adventurelog.png" }]],
  title: "AdventureLog",
  description: "The ultimate travel companion.",
  lang: "en-US",

  ignoreDeadLinks: [
    // ignore exact url "/playground"
    "/playground",
    // ignore all localhost links
    /^https?:\/\/localhost/,
    // ignore all links include "/repl/""
    /\/repl\//,
    // custom function, ignore all links include "ignore"
    (url) => {
      return url.toLowerCase().includes("ignore");
    },
  ],

  sitemap: {
    hostname: "https://adventurelog.app",
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

    footer: {
      message: "AdventureLog",
      copyright:
        'Copyright © 2023-2024 <a target="_blank" href="https:/seanmorley.com">Sean Morley</a>',
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
          { text: "Docker 🐋", link: "/docs/install/docker" },
          { text: "Proxmox LXC 🐧", link: "/docs/install/proxmox_lxc" },
          { text: "Synology NAS ☁️", link: "/docs/install/synology_nas" },

          {
            text: "With A Reverse Proxy",
            collapsed: false,
            items: [
              {
                text: "Nginx Proxy Manager",
                link: "/docs/install/nginx_proxy_manager",
              },
              { text: "Traefik", link: "/docs/install/traefik" },
            ],
          },
        ],
      },
      {
        text: "Configuration",
        collapsed: false,
        items: [
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
            text: "v0.7.1 Migration Guide",
            link: "/docs/guides/v0-7-1_migration",
          },
        ],
      },
      {
        text: "Changelogs",
        items: [
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
    ],
  },
});
