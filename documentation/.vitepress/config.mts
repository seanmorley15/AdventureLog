import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { defineConfig, type HeadConfig } from "vitepress";
import { faq } from "./faq";
import { announceUntil, getRepoMeta, REPO_URL } from "./github";
import { SHOT_SIZE, shotFallback, shots, type ShotName } from "./screenshots";
import {
  APP_ID,
  buildDocsJsonLd,
  buildPageHead,
  ORG_ID,
  pagePathToUrl,
  pageSeo,
  SITE_NAME,
  SITE_ORIGIN,
  WEBSITE_ID,
} from "./seo";
import { sidebar } from "./sidebar";

const FALLBACK_DESCRIPTION =
  "AdventureLog documentation for self-hosted travel tracking, trip planning, and Docker deployment.";

const SAME_AS = [
  REPO_URL,
  "https://discord.gg/wRbQ9Egr8C",
  "https://x.com/AdventureLogApp",
  "https://mastodon.social/@adventurelog",
  "https://www.instagram.com/adventurelogapp",
];

function jsonLd(graph: object): HeadConfig {
  return ["script", { type: "application/ld+json" }, JSON.stringify(graph)];
}

// https://vitepress.dev/reference/site-config
export default async () => {
  const repo = await getRepoMeta();
  // The release bar shows for a week after the release. The browser checks the
  // date too, so it disappears on time even without a rebuild.
  const announceEnd = announceUntil(repo);
  const announce = announceEnd !== null && Date.now() < announceEnd;

  return defineConfig({
    head: [
      [
        "link",
        {
          rel: "icon",
          type: "image/png",
          sizes: "512x512",
          href: "/adventurelog.png",
        },
      ],
      [
        "link",
        { rel: "icon", type: "image/svg+xml", href: "/adventurelog.svg" },
      ],
      ["link", { rel: "apple-touch-icon", href: "/apple-touch-icon.png" }],
      ["link", { rel: "manifest", href: "/site.webmanifest" }],
      [
        "meta",
        {
          name: "theme-color",
          media: "(prefers-color-scheme: light)",
          content: "#ffffff",
        },
      ],
      [
        "meta",
        {
          name: "theme-color",
          media: "(prefers-color-scheme: dark)",
          content: "#1b1b1f",
        },
      ],
      [
        "script",
        {
          defer: "",
          src: "https://cloud.umami.is/script.js",
          "data-website-id": "a7552764-5a1d-4fe7-80c2-5331e1a53cb6",
        },
      ],
      ["link", { rel: "me", href: "https://mastodon.social/@adventurelog" }],
      // Show the release announcement before first paint, for a week after the
      // release, unless this version was dismissed.
      ...(announce
        ? ([
            [
              "script",
              {},
              `if(Date.now()<${announceEnd}){try{if(localStorage.getItem("al-announce-dismissed")!==${JSON.stringify(repo.version)})document.documentElement.classList.add("al-announce")}catch(e){document.documentElement.classList.add("al-announce")}}`,
            ],
          ] as HeadConfig[])
        : []),
    ],
    ignoreDeadLinks: "localhostLinks",
    title: SITE_NAME,
    description:
      "Self-hosted, open-source travel companion for tracking locations, planning trips, and sharing adventures.",
    lang: "en-US",
    lastUpdated: true,
    markdown: {
      // Highlight ```env blocks instead of falling back to plain text.
      languageAlias: { env: "dotenv" },
    },

    sitemap: {
      hostname: SITE_ORIGIN,
      transformItems: (items) =>
        items.filter((item) => !/(^|\/)404(\.html)?$/.test(item.url)),
    },

    rewrites: {
      "docs/Guides/nginx_migration.md": "docs/guides/v0-7-1_migration.md",
      "docs/install/aio.md": "docs/install/standard.md",
    },

    transformPageData(pageData) {
      const isHome = pageData.relativePath === "index.md";
      const seo = pageSeo[pageData.relativePath] ?? {
        description: FALLBACK_DESCRIPTION,
      };
      const pageTitle = seo.title ?? pageData.title;
      // A page's own frontmatter description wins, as before; seo.ts fills the rest.
      const description =
        pageData.frontmatter.description ??
        seo.description ??
        pageData.description;
      const head = buildPageHead(pageData.relativePath, pageTitle, {
        ...seo,
        description,
      });

      if (isHome) {
        const app: Record<string, unknown> = {
          "@type": "SoftwareApplication",
          "@id": APP_ID,
          name: SITE_NAME,
          url: `${SITE_ORIGIN}/`,
          description,
          applicationCategory: "TravelApplication",
          applicationSubCategory: "Travel log and trip planner",
          operatingSystem: "Web, Docker, Linux, macOS, Windows",
          featureList: [
            "Location and visit logging with photos, notes, and ratings",
            "Interactive world map of visited and planned places",
            "Day-by-day trip itineraries with lodging, transport, and checklists",
            "Country, region, and city travel tracking",
            "Immich, Strava, Wanderer, Endurain, and Google Maps integrations",
            "OpenID Connect and social sign-in",
            "Self-hosted Docker deployment",
          ],
          screenshot: (Object.keys(shots) as ShotName[]).map((name) => ({
            "@type": "ImageObject",
            url: `${SITE_ORIGIN}${shotFallback(name, "light")}`,
            width: 1440,
            height: Math.round((1440 * SHOT_SIZE.height) / SHOT_SIZE.width),
            caption: shots[name],
          })),
          offers: {
            "@type": "Offer",
            price: "0",
            priceCurrency: "USD",
            description: "Free and open source to self-host.",
          },
          isAccessibleForFree: true,
          license: `${REPO_URL}/blob/main/LICENSE`,
          downloadUrl: REPO_URL,
          installUrl: `${SITE_ORIGIN}/docs/install/standard.html`,
          softwareHelp: `${SITE_ORIGIN}/docs/usage/usage.html`,
          codeRepository: REPO_URL,
          author: {
            "@type": "Person",
            name: "Sean Morley",
            url: "https://seanmorley.com",
          },
          publisher: { "@id": ORG_ID },
          keywords: (seo.keywords ?? []).join(", "),
        };
        if (repo.version) app.softwareVersion = repo.version.replace(/^v/, "");
        if (repo.releasedAt) app.dateModified = repo.releasedAt;
        if (repo.releaseUrl) app.releaseNotes = repo.releaseUrl;

        head.push(
          jsonLd({
            "@context": "https://schema.org",
            "@graph": [
              {
                "@type": "Organization",
                "@id": ORG_ID,
                name: SITE_NAME,
                url: `${SITE_ORIGIN}/`,
                logo: {
                  "@type": "ImageObject",
                  url: `${SITE_ORIGIN}/adventurelog.png`,
                  width: 512,
                  height: 512,
                },
                sameAs: SAME_AS,
              },
              {
                "@type": "WebSite",
                "@id": WEBSITE_ID,
                name: SITE_NAME,
                url: `${SITE_ORIGIN}/`,
                description,
                inLanguage: "en-US",
                publisher: { "@id": ORG_ID },
              },
              app,
              {
                "@type": "FAQPage",
                "@id": `${SITE_ORIGIN}/#faq`,
                mainEntity: faq.map((item) => ({
                  "@type": "Question",
                  name: item.question,
                  acceptedAnswer: { "@type": "Answer", text: item.answer },
                })),
              },
            ],
          }),
        );
      } else if (pageData.relativePath.startsWith("docs/")) {
        for (const graph of buildDocsJsonLd(
          pageData.relativePath,
          pageData.title,
          description,
          sidebar,
          pageData.lastUpdated,
        )) {
          head.push(jsonLd(graph));
        }
      }

      return {
        title: pageTitle,
        description,
        // The home title already names the product; skip the " | AdventureLog" suffix.
        ...(isHome ? { titleTemplate: false } : {}),
        frontmatter: {
          ...pageData.frontmatter,
          description,
          head: [...(pageData.frontmatter.head ?? []), ...head],
        },
      };
    },

    buildEnd(siteConfig) {
      const missing: string[] = [];
      const entries: string[] = [];

      // Pages in sidebar order, then anything the sidebar doesn't list.
      const order: string[] = [];
      const walk = (items: typeof sidebar) => {
        for (const item of items) {
          if (item.link?.startsWith("/"))
            order.push(`${item.link.slice(1)}.md`);
          if (item.items) walk(item.items);
        }
      };
      walk(sidebar);
      const rank = (page: string) => {
        const i = order.indexOf(page);
        return i === -1 ? order.length : i;
      };
      const pages = [...siteConfig.pages].sort(
        (a, b) => rank(a) - rank(b) || a.localeCompare(b),
      );

      for (const page of pages) {
        if (page === "404.md") continue;
        const seo = pageSeo[page];
        if (!seo) missing.push(page);

        let title = seo?.title;
        if (!title) {
          try {
            const source = readFileSync(join(siteConfig.srcDir, page), "utf8");
            title =
              source.match(/^title:\s*(.+)$/m)?.[1]?.trim() ??
              source.match(/^#\s+(.+)$/m)?.[1]?.trim();
          } catch {
            // Rewritten pages have no file at their output path; fall back below.
          }
        }
        title ??= page.replace(/\.md$/, "");
        const description = seo?.description ?? FALLBACK_DESCRIPTION;
        entries.push(
          `- [${title.replace(/[[\]]/g, "")}](${pagePathToUrl(page)}): ${description}`,
        );
      }

      if (missing.length) {
        console.warn(
          `\n[seo] ${missing.length} page(s) have no entry in .vitepress/seo.ts:\n  ${missing.join("\n  ")}\n`,
        );
      }

      const home = pageSeo["index.md"];
      const llms = [
        `# ${SITE_NAME}`,
        "",
        `> ${home.description}`,
        "",
        `AdventureLog is free and open source (GPL-3.0). Source code: ${REPO_URL}`,
        repo.version ? `Latest release: ${repo.version}` : "",
        "",
        "## Documentation",
        "",
        ...entries,
        "",
      ]
        .filter((line, i, all) => !(line === "" && all[i - 1] === ""))
        .join("\n");

      writeFileSync(join(siteConfig.outDir, "llms.txt"), llms);
    },

    themeConfig: {
      nav: [
        { text: "Home", link: "/" },
        { text: "Install", link: "/docs/install/getting_started" },
        {
          text: "Configure",
          link: "/docs/configuration/environment_variables",
        },
        { text: "Usage", link: "/docs/usage/usage" },
        {
          text: "GitHub",
          link: REPO_URL,
        },
      ],
      search: {
        provider: "local",
        options: {
          miniSearch: {
            searchOptions: {
              // Guides first: release notes mention everything, so rank them well below.
              // (Serialized to the client, so this must not use outside variables.)
              boostDocument: (id: string) =>
                id.includes("/changelogs/") ? 0.15 : 1,
            },
          },
        },
      },
      outline: { level: [2, 3], label: "On this page" },
      returnToTopLabel: "Back to top",
      sidebarMenuLabel: "Menu",
      darkModeSwitchLabel: "Theme",
      editLink: {
        pattern: `${REPO_URL}/edit/main/documentation/:path`,
      },
      lastUpdated: {
        text: "Last updated",
        formatOptions: { dateStyle: "medium" },
      },

      // No footer config: the theme renders its own SiteFooter instead.

      logo: "/adventurelog.png",

      sidebar,

      socialLinks: [
        { icon: "github", link: REPO_URL },
        { icon: "discord", link: "https://discord.gg/wRbQ9Egr8C" },
        { icon: "buymeacoffee", link: "https://buymeacoffee.com/seanmorley15" },
        { icon: "x", link: "https://x.com/AdventureLogApp" },
        { icon: "mastodon", link: "https://mastodon.social/@adventurelog" },
        {
          icon: "instagram",
          link: "https://www.instagram.com/adventurelogapp",
        },
      ],
    },
  });
};
