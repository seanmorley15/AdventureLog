/**
 * Homepage FAQ. Rendered visibly by HomeFaq.vue and emitted as FAQPage
 * structured data by config.mts, so the two never drift apart.
 *
 * `answer` is plain text (used in JSON-LD). `links` are optional follow-ups
 * shown under the visible answer only.
 */
export type FaqItem = {
  question: string;
  answer: string;
  links?: { text: string; href: string }[];
};

export const faq: FaqItem[] = [
  {
    question: "What is AdventureLog?",
    answer:
      "AdventureLog is an open-source, self-hosted travel companion. You save the places you've been as locations with photos and notes, plan trips with day-by-day itineraries, and track the countries and regions you've visited on an interactive world map.",
    links: [
      { text: "About AdventureLog", href: "/docs/intro/adventurelog_overview" },
    ],
  },
  {
    question: "Is AdventureLog free?",
    answer:
      "Yes. AdventureLog is free and open source under the GPL-3.0 license. Self-hosting it has no subscription and no feature limits.",
  },
  {
    question: "How do I install AdventureLog?",
    answer:
      "Most installs use Standard Deployment: one Docker container on port 8015 with a short .env file. The optional Quick Start installer walks you through the same setup interactively.",
    links: [
      { text: "Standard Deployment", href: "/docs/install/standard" },
      { text: "Quick Start installer", href: "/docs/install/quick_start" },
    ],
  },
  {
    question: "Can I run AdventureLog on a homelab or NAS?",
    answer:
      "Yes. AdventureLog runs anywhere Docker does, including homelab servers, a VPS, Proxmox, Synology NAS, Unraid, TrueNAS, Umbrel, and Kubernetes.",
    links: [
      { text: "All install options", href: "/docs/install/getting_started" },
    ],
  },
  {
    question: "Which apps does AdventureLog connect to?",
    answer:
      "AdventureLog can pull photos from Immich, activities from Strava and Endurain, and trails from Wanderer, and it can use Google Maps for place search. Sign-in works with OpenID Connect providers such as Authentik, Authelia, and Pocket ID.",
    links: [
      { text: "Immich", href: "/docs/configuration/immich_integration" },
      { text: "Strava", href: "/docs/configuration/strava_integration" },
      { text: "Social auth & OIDC", href: "/docs/configuration/social_auth" },
    ],
  },
  {
    question: "Can I share trips with other people?",
    answer:
      "Yes. Collections can be shared with other users on your instance so you can plan a trip together, and you can make individual locations or collections public.",
    links: [{ text: "Usage guide", href: "/docs/usage/usage" }],
  },
];
