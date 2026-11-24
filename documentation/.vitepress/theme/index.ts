import { h } from "vue";
import type { Theme } from "vitepress";
import DefaultTheme from "vitepress/theme";
import AnnouncementBar from "./components/AnnouncementBar.vue";
import AppShot from "./components/AppShot.vue";
import HomeHero from "./components/HomeHero.vue";
import ImageZoom from "./components/ImageZoom.vue";
import NotFound from "./components/NotFound.vue";
import SiteFooter from "./components/SiteFooter.vue";
import TableFilter from "./components/TableFilter.vue";
import "./style.css";
import "./home.css";
import "./editorial.css";

export default {
  extends: DefaultTheme,
  Layout: () => {
    return h(DefaultTheme.Layout, null, {
      "layout-top": () => h(AnnouncementBar),
      "home-hero-before": () => h(HomeHero),
      "not-found": () => h(NotFound),
      "layout-bottom": () => [h(SiteFooter), h(ImageZoom)],
    });
  },
  enhanceApp({ app }) {
    // Available in any markdown page.
    app.component("AppShot", AppShot);
    app.component("TableFilter", TableFilter);

    const components = import.meta.glob("./components/Home*.vue", {
      eager: true,
    }) as Record<string, { default: object }>;

    for (const path in components) {
      const name = path.split("/").pop()!.replace(".vue", "");
      if (name !== "HomeHero") {
        app.component(name, components[path].default);
      }
    }
  },
} satisfies Theme;
