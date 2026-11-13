import { announceUntil, getRepoMeta, type RepoMeta } from "./github";

export type RepoData = RepoMeta & {
  /** True when the build ran within a week of the latest release. */
  announce: boolean;
};

declare const data: RepoData;
export { data };

export default {
  async load(): Promise<RepoData> {
    const meta = await getRepoMeta();
    const until = announceUntil(meta);
    return { ...meta, announce: until !== null && Date.now() < until };
  },
};
