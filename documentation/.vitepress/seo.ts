import type { DefaultTheme, HeadConfig } from "vitepress";

export type PageSeo = {
  title?: string;
  description: string;
  keywords?: string[];
};

export const SITE_ORIGIN = "https://adventurelog.app";
export const SITE_NAME = "AdventureLog";

/** 1200×630 social card cropped from brand/banner.png (scripts/optimize-images.sh). */
export const OG_IMAGE = {
  url: `${SITE_ORIGIN}/og/adventurelog.jpg`,
  width: "1200",
  height: "630",
  type: "image/jpeg",
  alt: "AdventureLog logo, a folded paper map, over a mountain valley with the words The ultimate travel companion",
};

export const ORG_ID = `${SITE_ORIGIN}/#organization`;
export const WEBSITE_ID = `${SITE_ORIGIN}/#website`;
export const APP_ID = `${SITE_ORIGIN}/#software`;

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
    keywords: [
      "AdventureLog features",
      "open source travel app",
      "trip planning",
    ],
  },
  "docs/install/getting_started.md": {
    description:
      "Install AdventureLog with Standard Deployment — the default for most setups — plus optional guided installer, Advanced Deployment, Kubernetes, and platform guides.",
    keywords: [
      "AdventureLog install",
      "standard deployment docker",
      "self-hosted travel app setup",
    ],
  },
  "docs/install/quick_start.md": {
    description:
      "Optional guided installer for Standard Deployment. Interactive configuration, env file setup, and a built-in management menu for updates and backups.",
    keywords: [
      "AdventureLog quick start",
      "guided docker install",
      "standard deployment installer",
    ],
  },
  "docs/install/standard.md": {
    description:
      "The default AdventureLog install: one Docker container on a single port. Minimal .env configuration with automatic URL and secret derivation for homelabs and VPS.",
    keywords: [
      "AdventureLog standard deployment",
      "single container docker",
      "default docker install",
    ],
  },
  "docs/install/docker.md": {
    description:
      "Advanced Deployment for AdventureLog with separate frontend, backend, and PostGIS services. Full environment variable reference for production deployments.",
    keywords: ["AdventureLog docker compose", "self-hosted docker travel log"],
  },
  "docs/install/dev_container_wsl.md": {
    description:
      "Develop AdventureLog on Windows with WSL 2 and VS Code Dev Containers using docker/docker-compose.dev.yml and hot reload for frontend and backend.",
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
      "Deploy AdventureLog with Traefik using the official docker/docker-compose.traefik.yaml for automatic HTTPS and path-based routing.",
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
  "docs/usage/locations.md": {
    title: "Locations and Visits: Logging Where You've Been",
    description:
      "How to save locations in AdventureLog with photos, notes, ratings, categories, visits, trails, and activities, and how visited and planned locations work.",
    keywords: [
      "AdventureLog locations",
      "log travel places",
      "travel journal visits",
    ],
  },
  "docs/usage/trips.md": {
    title: "Trips and Collections: Plan an Itinerary Day by Day",
    description:
      "Plan a trip day by day in AdventureLog with locations, transport, lodging, notes, and checklists, then print a Trip Book or move the collection to another server.",
    keywords: [
      "AdventureLog trip planner",
      "day by day itinerary",
      "travel collections",
    ],
  },
  "docs/usage/map.md": {
    title: "The Map: Every Location You've Been or Plan to Go",
    description:
      "Use the AdventureLog map to see visited and planned locations, filter by category, show regions, photos, and GPX tracks, and search for new places nearby.",
    keywords: ["AdventureLog map", "travel map", "visited places map"],
  },
  "docs/usage/world_travel.md": {
    title: "World Travel: Track Countries, Regions, and Cities",
    description:
      "Track the countries, regions, and cities you've visited in AdventureLog, see complete and partial countries, and view them on a world map or globe.",
    keywords: [
      "AdventureLog world travel",
      "countries visited tracker",
      "regions visited",
    ],
  },
  "docs/usage/sharing.md": {
    title: "Sharing and Privacy: Plan Together and Publish Travel Stories",
    description:
      "Share an AdventureLog trip with editors and viewers, create guest links, publish a travel story, and control who can see your locations and profile.",
    keywords: [
      "AdventureLog sharing",
      "collaborative trip planning",
      "travel story",
    ],
  },
  "docs/configuration/integrations.md": {
    title:
      "Integrations: Immich, Strava, Wanderer, Endurain, Google Maps, and SSO",
    description:
      "Every service AdventureLog connects to: Immich photos, Strava and Endurain activities, Wanderer trails, Google Maps, OIDC single sign-on, S3 storage, and the API.",
    keywords: [
      "AdventureLog integrations",
      "Immich travel",
      "Strava import",
      "self-hosted SSO",
    ],
  },
  "docs/configuration/environment_variables.md": {
    description:
      "Complete AdventureLog environment variable reference for Standard Deployment, Advanced Deployment, and optional integrations including URLs, security, and storage.",
    keywords: [
      "AdventureLog environment variables",
      "docker env configuration",
    ],
  },
  "docs/configuration/operations.md": {
    description:
      "Operate AdventureLog in production: scripts/deploy.sh updates, backup and restore scripts, validate-env checks, management menu, and first-boot behavior.",
    keywords: ["AdventureLog backup", "deploy update", "docker operations"],
  },
  "docs/configuration/updating.md": {
    description:
      "Update AdventureLog Docker images safely with scripts/deploy.sh, the installer management menu, manual compose commands, and region data refresh.",
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
  "docs/configuration/endurain_integration.md": {
    description:
      "Connect a self-hosted Endurain instance to AdventureLog for JWT-authenticated activity browsing and GPX import into visits.",
    keywords: ["AdventureLog Endurain", "fitness integration", "GPX import"],
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
      "Fix 'Starting nginx: nginx failed' in older AdventureLog backend containers, caused by renaming the backend service.",
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
  "docs/install/first_steps.md": {
    title: "First Steps After Installing AdventureLog",
    description:
      "Find the generated AdventureLog admin password, secure the admin account, decide who can sign up, and set up email and backups after installing.",
    keywords: [
      "AdventureLog admin password",
      "AdventureLog default login",
      "after install",
    ],
  },
  "docs/install/production_checklist.md": {
    title: "Production Checklist for a Self-Hosted AdventureLog Server",
    description:
      "Everything to check before others rely on your AdventureLog server: HTTPS, admin account, registration, secrets, rate limits, email, storage, and backups.",
    keywords: ["AdventureLog production", "self-hosted security checklist"],
  },
  "docs/usage/settings.md": {
    title: "Account and Settings: Profile, Security, and Your Data",
    description:
      "Manage your AdventureLog profile and visibility, emails, password, multi-factor authentication, API keys, connected apps, and account backups.",
    keywords: [
      "AdventureLog settings",
      "AdventureLog MFA",
      "export AdventureLog data",
    ],
  },
  "docs/configuration/backups.md": {
    title: "Backups and Restore",
    description:
      "Back up and restore a self-hosted AdventureLog server: the PostgreSQL database, the media volume, and the env file, by script or by hand, and on a schedule.",
    keywords: ["AdventureLog backup", "restore AdventureLog", "PostGIS backup"],
  },
  "docs/configuration/management_commands.md": {
    title: "Management Commands",
    description:
      "AdventureLog command-line tools for admins: reset a password, import world data, fix territory locations, backfill photo coordinates, and clean up files.",
    keywords: [
      "AdventureLog manage.py",
      "download_countries",
      "admin commands",
    ],
  },
  "docs/guides/switch_to_standard.md": {
    title: "Switch from Advanced to Standard Deployment",
    description:
      "Move an existing AdventureLog Advanced Deployment to Standard Deployment with one container, keeping every user, location, collection, and photo.",
    keywords: ["AdventureLog migrate", "Standard Deployment migration"],
  },
  "docs/troubleshooting/common_issues.md": {
    title: "Common Issues and Fixes",
    description:
      "Fix common AdventureLog problems: the admin password, login and CSRF errors, missing photos, 502 errors, empty world data, stuck jobs, and integrations that can't connect.",
    keywords: ["AdventureLog troubleshooting", "AdventureLog not working"],
  },
  "docs/changelogs/development_timeline.md": {
    description:
      "The origin story and development timeline of AdventureLog from first commit to a full-featured self-hosted travel platform.",
    keywords: ["AdventureLog history", "development timeline"],
  },
  "docs/install/easypanel.md": {
    description:
      "Deploy AdventureLog on Easypanel with the official one-click template, including the PostGIS database and a public domain.",
    keywords: ["AdventureLog Easypanel", "one-click deploy"],
  },
  "docs/configuration/caching.md": {
    description:
      "What AdventureLog caches, for how long, and how to tune or clear it: OpenStreetMap lookups, Wanderer trails, GPX map data, and login sessions.",
    keywords: ["AdventureLog caching", "OSM cache", "performance"],
  },
  "docs/configuration/background_jobs.md": {
    description:
      "How AdventureLog runs slow work in a built-in background worker: geocoding, emails, exports and imports, scheduled tasks, and how to check the queue.",
    keywords: ["AdventureLog background jobs", "worker", "scheduled tasks"],
  },
  "docs/configuration/public_access.md": {
    description:
      "Make a self-hosted AdventureLog server private with ALLOW_PUBLIC_ACCESS, and see what visitors without an account can and can't view.",
    keywords: [
      "AdventureLog public access",
      "private instance",
      "ALLOW_PUBLIC_ACCESS",
    ],
  },
  "docs/changelogs/v0-14-0.md": {
    description:
      "AdventureLog v0.14.0 Abisko release: day-by-day trip planning, rebuilt sharing with roles and guest links, comments, the printable Trip Book, and a documented API.",
    keywords: ["AdventureLog v0.14.0 changelog", "Abisko release"],
  },
  "docs/changelogs/v0-13-1.md": {
    description:
      "AdventureLog v0.13.1 Cadillac release: duplicate-place detection, a preferred date format, faster visit logging, richer collection exports, and security updates.",
    keywords: ["AdventureLog v0.13.1 changelog", "Cadillac release"],
  },
  "docs/changelogs/v0-13-0.md": {
    description:
      "AdventureLog v0.13.0 Acadia release: dashboard, travel calendar, global search, PDF exports, Endurain integration, and self-hosting improvements.",
    keywords: ["AdventureLog v0.13.0 changelog", "Acadia release"],
  },
  "docs/changelogs/v0-12-1.md": {
    description:
      "AdventureLog v0.12.1 release notes, bug fixes, and improvements.",
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
): HeadConfig[] {
  const isHome = relativePath === "index.md";
  const description = seo.description;
  const canonicalUrl = pagePathToUrl(relativePath);
  const ogTitle = seo.title ?? pageTitle;

  const head: HeadConfig[] = [
    ["meta", { name: "description", content: description }],
    ["meta", { property: "og:title", content: ogTitle }],
    ["meta", { property: "og:description", content: description }],
    ["meta", { property: "og:url", content: canonicalUrl }],
    ["meta", { property: "og:type", content: isHome ? "website" : "article" }],
    ["meta", { property: "og:site_name", content: SITE_NAME }],
    ["meta", { property: "og:locale", content: "en_US" }],
    ["meta", { property: "og:image", content: OG_IMAGE.url }],
    ["meta", { property: "og:image:type", content: OG_IMAGE.type }],
    ["meta", { property: "og:image:width", content: OG_IMAGE.width }],
    ["meta", { property: "og:image:height", content: OG_IMAGE.height }],
    ["meta", { property: "og:image:alt", content: OG_IMAGE.alt }],
    ["meta", { name: "twitter:card", content: "summary_large_image" }],
    ["meta", { name: "twitter:site", content: "@AdventureLogApp" }],
    ["meta", { name: "twitter:title", content: ogTitle }],
    ["meta", { name: "twitter:description", content: description }],
    ["meta", { name: "twitter:image", content: OG_IMAGE.url }],
    ["meta", { name: "twitter:image:alt", content: OG_IMAGE.alt }],
    ["link", { rel: "canonical", href: canonicalUrl }],
  ];

  if (seo.keywords?.length) {
    head.push(["meta", { name: "keywords", content: seo.keywords.join(", ") }]);
  }

  return head;
}

type Crumb = { name: string; url?: string };

/**
 * Walks the sidebar to find the trail of group titles leading to a page.
 * Groups without a link of their own are emitted without a URL.
 */
function findTrail(
  items: DefaultTheme.SidebarItem[],
  link: string,
  trail: Crumb[] = [],
): Crumb[] | null {
  for (const item of items) {
    const here: Crumb = {
      name: item.text ?? "",
      url: item.link ? linkToUrl(item.link) : undefined,
    };
    if (item.link && normalizeLink(item.link) === link) {
      return [...trail, here];
    }
    if (item.items) {
      const found = findTrail(item.items, link, [...trail, here]);
      if (found) return found;
    }
  }
  return null;
}

function normalizeLink(link: string): string {
  return link.replace(/\.(md|html)$/, "").replace(/\/$/, "");
}

function linkToUrl(link: string): string | undefined {
  if (/^https?:/.test(link)) return undefined;
  return `${SITE_ORIGIN}${normalizeLink(link)}.html`;
}

/** BreadcrumbList + TechArticle for a docs page. */
export function buildDocsJsonLd(
  relativePath: string,
  title: string,
  description: string,
  sidebar: DefaultTheme.SidebarItem[],
  lastUpdated?: number,
): object[] {
  const url = pagePathToUrl(relativePath);
  const link = "/" + relativePath.replace(/\.md$/, "");
  const trail = findTrail(sidebar, link) ?? [{ name: title, url }];

  // Search engines need a URL on every crumb but the last, so sidebar groups
  // that are only headings (no page of their own) are left out.
  const crumbs: Crumb[] = [
    { name: "Home", url: `${SITE_ORIGIN}/` },
    ...trail.slice(0, -1).filter((c) => c.url && c.url !== url),
    { name: title, url },
  ];

  const breadcrumb = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: crumbs.map((c, i) => ({
      "@type": "ListItem",
      position: i + 1,
      name: c.name,
      ...(c.url ? { item: c.url } : {}),
    })),
  };

  const article = {
    "@context": "https://schema.org",
    "@type": "TechArticle",
    "@id": `${url}#article`,
    headline: title,
    description,
    url,
    mainEntityOfPage: url,
    inLanguage: "en-US",
    image: OG_IMAGE.url,
    ...(lastUpdated
      ? { dateModified: new Date(lastUpdated).toISOString() }
      : {}),
    isPartOf: { "@id": WEBSITE_ID },
    about: { "@id": APP_ID },
    publisher: { "@id": ORG_ID },
    author: { "@id": ORG_ID },
  };

  return [breadcrumb, article];
}
