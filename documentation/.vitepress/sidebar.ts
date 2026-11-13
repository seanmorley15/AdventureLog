import type { DefaultTheme } from "vitepress";

/** Docs sidebar. Also used to build BreadcrumbList structured data (seo.ts). */
export const sidebar: DefaultTheme.SidebarItem[] = [
  {
    text: "Get Started",
    items: [
      { text: "About AdventureLog", link: "/docs/intro/adventurelog_overview" },
      { text: "Install AdventureLog", link: "/docs/install/getting_started" },
      { text: "Standard Deployment", link: "/docs/install/standard" },
      { text: "Quick Start Installer", link: "/docs/install/quick_start" },
      { text: "First Steps", link: "/docs/install/first_steps" },
      {
        text: "Production Checklist",
        link: "/docs/install/production_checklist",
      },
    ],
  },
  {
    text: "Use AdventureLog",
    collapsed: false,
    items: [
      { text: "How to Use AdventureLog", link: "/docs/usage/usage" },
      { text: "Locations and Visits", link: "/docs/usage/locations" },
      { text: "Trips and Collections", link: "/docs/usage/trips" },
      { text: "The Map", link: "/docs/usage/map" },
      { text: "World Travel", link: "/docs/usage/world_travel" },
      { text: "Sharing and Privacy", link: "/docs/usage/sharing" },
      { text: "Account and Settings", link: "/docs/usage/settings" },
    ],
  },
  {
    text: "Self-Host",
    collapsed: false,
    items: [
      { text: "Advanced Deployment", link: "/docs/install/docker" },
      {
        text: "Platform Guides",
        collapsed: true,
        items: [
          { text: "Proxmox LXC", link: "/docs/install/proxmox_lxc" },
          { text: "Synology NAS", link: "/docs/install/synology_nas" },
          { text: "Unraid", link: "/docs/install/unraid" },
          { text: "Easypanel", link: "/docs/install/easypanel" },
          { text: "Kubernetes", link: "/docs/install/kustomize" },
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
    text: "Configure",
    collapsed: false,
    items: [
      {
        text: "Sign-in and Access",
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
            text: "Pocket ID",
            link: "/docs/configuration/social_auth/pocket_id",
          },
          {
            text: "Authelia",
            link: "https://www.authelia.com/integration/openid-connect/adventure-log/",
          },
          {
            text: "OpenID Connect",
            link: "/docs/configuration/social_auth/oidc",
          },
          {
            text: "GitHub",
            link: "/docs/configuration/social_auth/github",
          },
          {
            text: "Disable Registration",
            link: "/docs/configuration/disable_registration",
          },
          { text: "Invite a User", link: "/docs/guides/invite_user" },
          {
            text: "Public Access",
            link: "/docs/configuration/public_access",
          },
        ],
      },
      {
        text: "Integrations",
        collapsed: true,
        items: [
          {
            text: "All Integrations",
            link: "/docs/configuration/integrations",
          },
          {
            text: "Immich",
            link: "/docs/configuration/immich_integration",
          },
          {
            text: "Strava",
            link: "/docs/configuration/strava_integration",
          },
          {
            text: "Endurain",
            link: "/docs/configuration/endurain_integration",
          },
          {
            text: "Wanderer",
            link: "/docs/configuration/wanderer_integration",
          },
          {
            text: "Google Maps",
            link: "/docs/configuration/google_maps_integration",
          },
        ],
      },
      {
        text: "S3 Media Storage",
        link: "/docs/configuration/s3_storage",
      },
      { text: "SMTP Email", link: "/docs/configuration/email" },
      { text: "Caching", link: "/docs/configuration/caching" },
      {
        text: "Background Jobs",
        link: "/docs/configuration/background_jobs",
      },
      {
        text: "Advanced Settings",
        link: "/docs/configuration/advanced_configuration",
      },
      { text: "Umami Analytics", link: "/docs/configuration/analytics" },
    ],
  },
  {
    text: "Maintain",
    collapsed: false,
    items: [
      { text: "Updating", link: "/docs/configuration/updating" },
      { text: "Backups and Restore", link: "/docs/configuration/backups" },
      { text: "Operations", link: "/docs/configuration/operations" },
      {
        text: "Management Commands",
        link: "/docs/configuration/management_commands",
      },
      { text: "Admin Panel", link: "/docs/guides/admin_panel" },
      {
        text: "Migrations",
        collapsed: true,
        items: [
          {
            text: "Switch to Standard Deployment",
            link: "/docs/guides/switch_to_standard",
          },
          {
            text: "v0.7.1 Migration",
            link: "/docs/guides/v0-7-1_migration",
          },
        ],
      },
    ],
  },
  {
    text: "Troubleshooting",
    collapsed: true,
    items: [
      {
        text: "Common Issues",
        link: "/docs/troubleshooting/common_issues",
      },
      {
        text: "Login Unresponsive",
        link: "/docs/troubleshooting/login_unresponsive",
      },
      {
        text: "Images Not Displaying",
        link: "/docs/troubleshooting/no_images",
      },
      {
        text: "Nginx Failed to Start",
        link: "/docs/troubleshooting/nginx_failed",
      },
    ],
  },
  {
    text: "Reference",
    collapsed: false,
    items: [
      {
        text: "Environment Variables",
        link: "/docs/configuration/environment_variables",
      },
      { text: "API Keys", link: "/docs/configuration/api_keys" },
    ],
  },
  {
    text: "Contribute",
    collapsed: true,
    items: [
      {
        text: "Development Setup",
        link: "/docs/install/dev_container_wsl",
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
      { text: "v0.14.0", link: "/docs/changelogs/v0-14-0" },
      { text: "v0.13.1", link: "/docs/changelogs/v0-13-1" },
      { text: "v0.13.0", link: "/docs/changelogs/v0-13-0" },
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
];
