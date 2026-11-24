/**
 * Live repository facts, fetched once at build time.
 *
 * Every field is null when GitHub can't be reached; callers omit whatever is
 * missing rather than guessing. Set GITHUB_TOKEN in the build
 * environment to avoid the anonymous API rate limit.
 */
export type RepoMeta = {
  stars: number | null;
  /** Latest published release tag, e.g. "v0.13.1". */
  version: string | null;
  releaseUrl: string | null;
  releasedAt: string | null;
};

export const REPO = "seanmorley15/AdventureLog";
export const REPO_URL = `https://github.com/${REPO}`;

const EMPTY: RepoMeta = {
  stars: null,
  version: null,
  releaseUrl: null,
  releasedAt: null,
};

let cached: Promise<RepoMeta> | undefined;

async function getJson(path: string): Promise<any | null> {
  const headers: Record<string, string> = {
    Accept: "application/vnd.github+json",
    "User-Agent": "adventurelog-docs-build",
  };
  if (process.env.GITHUB_TOKEN) {
    headers.Authorization = `Bearer ${process.env.GITHUB_TOKEN}`;
  }
  try {
    const res = await fetch(`https://api.github.com/repos/${REPO}${path}`, {
      headers,
      signal: AbortSignal.timeout(5000),
    });
    if (!res.ok) {
      console.warn(`[github] ${path || "/"} returned ${res.status}`);
      return null;
    }
    return await res.json();
  } catch (error) {
    console.warn(`[github] ${path || "/"} failed: ${(error as Error).message}`);
    return null;
  }
}

export function getRepoMeta(): Promise<RepoMeta> {
  if (process.env.DOCS_OFFLINE) return Promise.resolve(EMPTY);

  cached ??= (async () => {
    const [repo, release] = await Promise.all([
      getJson(""),
      getJson("/releases/latest"),
    ]);
    return {
      stars:
        typeof repo?.stargazers_count === "number"
          ? repo.stargazers_count
          : null,
      version: typeof release?.tag_name === "string" ? release.tag_name : null,
      releaseUrl:
        typeof release?.html_url === "string" ? release.html_url : null,
      releasedAt:
        typeof release?.published_at === "string" ? release.published_at : null,
    };
  })();

  return cached;
}

/** How long the release announcement bar stays up after a release. */
export const ANNOUNCE_DAYS = 7;

/**
 * When the announcement for the latest release stops showing, in epoch ms, or
 * null when there is no release date to count from.
 */
export function announceUntil(meta: RepoMeta): number | null {
  if (!meta.version || !meta.releasedAt) return null;
  const released = Date.parse(meta.releasedAt);
  if (Number.isNaN(released)) return null;
  return released + ANNOUNCE_DAYS * 24 * 60 * 60 * 1000;
}
