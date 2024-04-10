import { vitePreprocess } from "@sveltejs/vite-plugin-svelte";
import adapterNode from "@sveltejs/adapter-node";
import adapterVercel from "@sveltejs/adapter-vercel";

let adapter;
if (process.env.USING_VERCEL === "true") {
  adapter = adapterVercel;
} else {
  adapter = adapterNode;
}

/** @type {import('@sveltejs/kit').Config} */
const config = {
  preprocess: vitePreprocess(),
  kit: {
    adapter: adapter(),
    csrf: { checkOrigin: true, }
  },
};

export default config;
