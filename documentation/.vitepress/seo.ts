export type PageSeo = {
  title?: string;
  description: string;
  keywords?: string[];
};

const DEFAULT_OG_IMAGE =
  "https://raw.githubusercontent.com/seanmorley15/AdventureLog/refs/heads/main/brand/screenshots/adventures.png";

const SITE_ORIGIN = "https://adventurelog.app";

/** Per-page SEO metadata keyed by VitePress relativePath. URLs are preserved for search rankings. */
export const pageSeo: Record<string, PageSeo> = {
  "index.md": {
    title: "AdventureLog — Travel Log, Trip Planner & World Map",
    description:
      "Log locations with photos and notes, plan multi-day itineraries with flights and lodging, and track countries on an interactive world map. AdventureLog is the open-source travel companion for remembering every trip.",
    keywords: [
      "travel log app",
      "trip planner",
      "world travel tracker",
      "travel itinerary app",
      "location travel journal",
      "interactive travel map",
      "open source travel app",
      "AdventureLog",
    ],
  },
  "docs/intro/adventurelog_overview.md": {
    description:
      "Learn what AdventureLog is, its core features for location tracking and trip planning, and why it is a modern open-source alternative to closed travel apps.",
    keywords: ["AdventureLog features", "open source travel app", "trip planning"],
  },
  "docs/install/getting_started.md": {
    description:
      "Install AdventureLog with All-in-One Docker — the default for most setups — plus optional guided installer, standard Docker, Kubernetes, and platform guides.",
    keywords: ["AdventureLog install", "AIO docker", "self-hosted travel app setup"],
  },
  "docs/install/quick_start.md": {
    description:
      "Optional guided installer for All-in-One Docker. Interactive configuration, env file setup, and a built-in management menu for updates and backups.",
    keywords: ["AdventureLog quick start", "guided docker install", "AIO installer"],
  },
  "docs/install/aio.md": {
    description:
      "The default AdventureLog install: one Docker container on a single port. Minimal .env.aio configuration with automatic URL and secret derivation for homelabs and VPS.",
    keywords: ["AdventureLog AIO", "all in one docker", "default docker install"],
  },
  "docs/install/docker.md": {
    description:
      "Standard multi-container Docker setup for AdventureLog with separate frontend, backend, and PostGIS services. Full environment variable reference for production deployments.",
    keywords: ["AdventureLog docker compose", "self-hosted docker travel log"],
  },
  "docs/install/dev_container_wsl.md": {
    description:
      "Develop AdventureLog on Windows with WSL 2 and VS Code Dev Containers using docker-compose.dev.yml and hot reload for frontend and backend.",
    keywords: ["AdventureLog development", "dev container", "WSL docker"],
  },
  "docs/install/proxmox_lxc.md": {
    description:
      "Install AdventureLog on Proxmox using an LXC container with Docker for a lightweight homelab deployment.",
    keywords: ["AdventureLog Proxmox", "LXC homelab install"],
  },
  "docs/install/synology_nas.md": {
    description:
      "Self-host AdventureLog on a Synology NAS using Docker or Container Manager with step-by-step setup guidance.",
    keywords: ["AdventureLog Synology", "NAS docker install"],
  },
  "docs/install/kustomize.md": {
    description:
      "Deploy AdventureLog on Kubernetes with Kustomize manifests in k8s/base/, including PostGIS and ingress configuration.",
    keywords: ["AdventureLog kubernetes", "kustomize deployment"],
  },
  "docs/install/unraid.md": {
    description:
      "Install AdventureLog on Unraid with Docker templates for frontend, backend, and PostGIS database containers.",
    keywords: ["AdventureLog Unraid", "homelab docker template"],
  },
  "docs/install/nginx_proxy_manager.md": {
    description:
      "Put AdventureLog behind Nginx Proxy Manager with HTTPS, path routing, and trusted origin configuration for Django and SvelteKit.",
    keywords: ["AdventureLog nginx proxy manager", "reverse proxy HTTPS"],
  },
  "docs/install/traefik.md": {
    description:
      "Deploy AdventureLog with Traefik using the official docker-compose-traefik.yaml for automatic HTTPS and path-based routing.",
    keywords: ["AdventureLog Traefik", "docker reverse proxy"],
  },
  "docs/install/caddy.md": {
    description:
      "Run AdventureLog behind Caddy for automatic HTTPS and simple reverse proxy configuration on a single domain.",
    keywords: ["AdventureLog Caddy", "automatic HTTPS proxy"],
  },
  "docs/usage/usage.md": {
    description:
      "User guide for AdventureLog: locations, visits, collections, itineraries, world travel, integrations, and collaborative trip planning.",
    keywords: ["how to use AdventureLog", "travel log tutorial"],
  },
  "docs/configuration/environment_variables.md": {
    description:
      "Complete AdventureLog environment variable reference for standard Docker, AIO, and optional integrations including URLs, security, and storage.",
    keywords: ["AdventureLog environment variables", "docker env configuration"],
  },
  "docs/configuration/operations.md": {
    description:
      "Operate AdventureLog in production: deploy.sh updates, backup and restore scripts, validate-env checks, management menu, and first-boot behavior.",
    keywords: ["AdventureLog backup", "deploy update", "docker operations"],
  },
  "docs/configuration/updating.md": {
    description:
      "Update AdventureLog Docker images safely with deploy.sh, the installer management menu, manual compose commands, and region data refresh.",
    keywords: ["AdventureLog update", "docker pull upgrade"],
  },
  "docs/configuration/immich_integration.md": {
    description:
      "Connect AdventureLog to Immich for photo imports and linking images to travel locations from your self-hosted media library.",
    keywords: ["AdventureLog Immich integration", "photo travel log"],
  },
  "docs/configuration/google_maps_integration.md": {
    description:
      "Enable Google Maps in AdventureLog for enhanced map tiles and place search using a Google Maps API key.",
    keywords: ["AdventureLog Google Maps", "maps API key"],
  },
  "docs/configuration/strava_integration.md": {
    description:
      "Import Strava activities into AdventureLog locations with GPX tracks, distance, and elevation data.",
    keywords: ["AdventureLog Strava", "activity import"],
  },
  "docs/configuration/wanderer_integration.md": {
    description:
      "Link Wanderer trails to AdventureLog locations for hiking routes with distance and elevation context.",
    keywords: ["AdventureLog Wanderer", "trail integration"],
  },
  "docs/configuration/social_auth.md": {
    description:
      "Configure social and OIDC login for AdventureLog with GitHub, Authentik, Pocket ID, Authelia, and generic OpenID Connect providers.",
    keywords: ["AdventureLog OIDC", "social login self-hosted"],
  },
  "docs/configuration/social_auth/authentik.md": {
    description:
      "Set up Authentik as an OpenID Connect provider for AdventureLog single sign-on and account linking.",
    keywords: ["AdventureLog Authentik", "OIDC SSO"],
  },
  "docs/configuration/social_auth/github.md": {
    description:
      "Enable GitHub OAuth login for AdventureLog using django-allauth social application configuration.",
    keywords: ["AdventureLog GitHub login", "OAuth"],
  },
  "docs/configuration/social_auth/pocket_id.md": {
    description:
      "Configure Pocket ID as an OIDC identity provider for AdventureLog authentication.",
    keywords: ["AdventureLog Pocket ID", "OIDC login"],
  },
  "docs/configuration/social_auth/oidc.md": {
    description:
      "Connect any OpenID Connect provider to AdventureLog for enterprise or self-hosted identity management.",
    keywords: ["AdventureLog OpenID Connect", "generic OIDC"],
  },
  "docs/configuration/disable_registration.md": {
    description:
      "Disable public user registration on a self-hosted AdventureLog instance while keeping invites and social signup options.",
    keywords: ["AdventureLog disable registration", "private instance"],
  },
  "docs/configuration/email.md": {
    description:
      "Configure SMTP email in AdventureLog for account verification, password reset, and invitation messages.",
    keywords: ["AdventureLog SMTP", "email configuration"],
  },
  "docs/configuration/analytics.md": {
    description:
      "Optionally add Umami analytics to AdventureLog for privacy-friendly usage tracking on your self-hosted instance.",
    keywords: ["AdventureLog Umami analytics"],
  },
  "docs/configuration/s3_storage.md": {
    description:
      "Store AdventureLog media on S3-compatible object storage including AWS S3, Cloudflare R2, MinIO, and DigitalOcean Spaces.",
    keywords: ["AdventureLog S3 storage", "R2 media", "object storage"],
  },
  "docs/configuration/api_keys.md": {
    description:
      "Create and use AdventureLog REST API keys for scripts and integrations with the locations, collections, and stats endpoints.",
    keywords: ["AdventureLog API keys", "REST API authentication"],
  },
  "docs/configuration/advanced_configuration.md": {
    description:
      "Advanced AdventureLog settings: rate limits, Gunicorn workers, email verification, social-only login, and first-boot world data options.",
    keywords: ["AdventureLog advanced config", "rate limits", "gunicorn"],
  },
  "docs/troubleshooting/no_images.md": {
    description:
      "Fix AdventureLog images not displaying: URL configuration, media paths, S3 settings, and reverse proxy routing for /media.",
    keywords: ["AdventureLog images not showing", "media troubleshooting"],
  },
  "docs/troubleshooting/login_unresponsive.md": {
    description:
      "Resolve AdventureLog login and registration failures caused by CSRF, ORIGIN, SITE_URL, or reverse proxy misconfiguration.",
    keywords: ["AdventureLog login broken", "CSRF troubleshooting"],
  },
  "docs/troubleshooting/nginx_failed.md": {
    description:
      "Diagnose 'Starting nginx: nginx failed' errors in the AdventureLog backend container during Docker startup.",
    keywords: ["AdventureLog nginx failed", "backend container error"],
  },
  "docs/guides/admin_panel.md": {
    description:
      "Use the Django admin panel at /admin to manage AdventureLog users, locations, and database objects as a staff administrator.",
    keywords: ["AdventureLog admin panel", "Django admin"],
  },
  "docs/guides/invite_user.md": {
    description:
      "Invite users to a private AdventureLog instance using django-invitations from the admin panel or in-app invite flow.",
    keywords: ["AdventureLog invite user", "private instance"],
  },
  "docs/guides/v0-7-1_migration.md": {
    description:
      "Migrate AdventureLog to v0.7.1 with the updated in-container nginx and gunicorn Docker Compose layout.",
    keywords: ["AdventureLog v0.7.1 migration", "nginx migration"],
  },
  "docs/changelogs/development_timeline.md": {
    description:
      "The origin story and development timeline of AdventureLog from first commit to a full-featured self-hosted travel platform.",
    keywords: ["AdventureLog history", "development timeline"],
  },
  "docs/changelogs/v0-12-1.md": {
    description: "AdventureLog v0.12.1 release notes, bug fixes, and improvements.",
    keywords: ["AdventureLog v0.12.1 changelog"],
  },
  "docs/changelogs/v0-12-0.md": {
    description:
      "AdventureLog v0.12.0 release: trip planning improvements, itineraries, and budget features.",
    keywords: ["AdventureLog v0.12.0 changelog"],
  },
  "docs/changelogs/v0-11-0.md": {
    description:
      "AdventureLog v0.11.0 release: Strava and Wanderer integrations, redesigned UI, and new features.",
    keywords: ["AdventureLog v0.11.0 changelog"],
  },
  "docs/changelogs/v0-10-0.md": {
    description:
      "AdventureLog v0.10.0 release: trip maps, Google Maps integration, and quick deploy script.",
    keywords: ["AdventureLog v0.10.0 changelog"],
  },
  "docs/changelogs/v0-9-0.md": {
    description:
      "AdventureLog v0.9.0 release: smart recommendations, attachments, and map improvements.",
    keywords: ["AdventureLog v0.9.0 changelog"],
  },
  "docs/changelogs/v0-8-0.md": {
    description:
      "AdventureLog v0.8.0 release: Immich integration, calendar view, and UI customization.",
    keywords: ["AdventureLog v0.8.0 changelog"],
  },
  "docs/changelogs/v0-7-1.md": {
    description:
      "AdventureLog v0.7.1 release: in-container nginx migration, gunicorn, and adventure sorting improvements.",
    keywords: ["AdventureLog v0.7.1 changelog"],
  },
  "docs/changelogs/v0-7-0.md": {
    description: "AdventureLog v0.7.0 release notes and feature summary.",
    keywords: ["AdventureLog v0.7.0 changelog"],
  },
};

export function pagePathToUrl(relativePath: string): string {
  if (relativePath === "index.md") {
    return `${SITE_ORIGIN}/`;
  }

  const slug = relativePath.replace(/\.md$/, "").replace(/\/index$/, "");
  return `${SITE_ORIGIN}/${slug}.html`;
}

export function buildPageHead(
  relativePath: string,
  pageTitle: string,
  seo: PageSeo,
): Array<[string, Record<string, string>] | [string, Record<string, string>, string]> {
  const description = seo.description;
  const canonicalUrl = pagePathToUrl(relativePath);
  const ogTitle = seo.title ?? pageTitle;

  const head: Array<
    [string, Record<string, string>] | [string, Record<string, string>, string]
  > = [
    ["meta", { name: "description", content: description }],
    ["meta", { property: "og:title", content: ogTitle }],
    ["meta", { property: "og:description", content: description }],
    ["meta", { property: "og:url", content: canonicalUrl }],
    ["meta", { property: "og:type", content: "article" }],
    ["meta", { property: "og:image", content: DEFAULT_OG_IMAGE }],
    ["meta", { property: "og:site_name", content: "AdventureLog" }],
    ["meta", { name: "twitter:card", content: "summary_large_image" }],
    ["meta", { name: "twitter:title", content: ogTitle }],
    ["meta", { name: "twitter:description", content: description }],
    ["meta", { name: "twitter:image", content: DEFAULT_OG_IMAGE }],
    ["link", { rel: "canonical", href: canonicalUrl }],
  ];

  if (seo.keywords?.length) {
    head.push(["meta", { name: "keywords", content: seo.keywords.join(", ") }]);
  }

  return head;
}

export { DEFAULT_OG_IMAGE, SITE_ORIGIN };
