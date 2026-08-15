import { h } from "vue";
import type { Theme } from "vitepress";
import DefaultTheme from "vitepress/theme";
import HomeHero from "./components/HomeHero.vue";
import HomeFeatures from "./components/HomeFeatures.vue";
import SiteFooter from "./components/SiteFooter.vue";
import "./style.css";
import "./home.css";

export default {
  extends: DefaultTheme,
  Layout: () => {
    return h(DefaultTheme.Layout, null, {
      "home-hero-before": () => h(HomeHero),
      "home-features-before": () => h(HomeFeatures),
      "layout-bottom": () => h(SiteFooter),
    });
  },
  enhanceApp({ app }) {
    const components = import.meta.glob("./components/Home*.vue", {
      eager: true,
    }) as Record<string, { default: object }>;

    for (const path in components) {
      const name = path.split("/").pop()!.replace(".vue", "");
      if (name !== "HomeHero" && name !== "HomeFeatures") {
        app.component(name, components[path].default);
      }
    }
  },
} satisfies Theme;
