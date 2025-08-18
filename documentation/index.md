---
# https://vitepress.dev/reference/default-theme-home-page
layout: home

hero:
  name: "AdventureLog"
  text: "The ultimate travel companion."
  tagline: Discover new places, track your adventures, and share your experiences with friends and family.
  actions:
    - theme: brand
      text: Get Started
      link: /docs/install/getting_started
    - theme: alt
      text: About
      link: /docs/intro/adventurelog_overview
    - theme: alt
      text: Demo
      link: https://demo.adventurelog.app
  image:
    src: ./adventurelog.svg
    alt: AdventureLog Map Logo

features:
  - title: "Track Your Adventures"
    details: "Log your adventures and keep track of where you've been on the world map."
    icon: 📍
  - title: "Plan Your Next Trip"
    details: "Take the guesswork out of planning your next adventure with an easy-to-use itinerary planner."
    icon: 📅
  - title: "Share Your Experiences"
    details: "Share your adventures with friends and family and collaborate on trips together."
    icon: 📸
---

## ⚡️ Quick Start

Get AdventureLog running in under 60 seconds:

```bash [One-Line Install]
curl -sSL https://get.adventurelog.app | bash
```

You can also explore our [full installation guide](/docs/install/getting_started) for plenty of options, including Docker, Proxmox, Synology NAS, and more.

## 📸 See It In Action

::: details 🗂️ **Location Overview & Management**  
Manage your full list of locations with ease. View upcoming and past trips, filter and sort by status, date, or category to find exactly what you want quickly.  
<img src="https://raw.githubusercontent.com/seanmorley15/AdventureLog/refs/heads/main/brand/screenshots/adventures.png" alt="Location Overview" style="max-width:100%; margin-top:10px;" />  
:::

::: details 📋 **Detailed Adventure Logs**  
Capture rich details for every location: name, dates, precise locations, vivid descriptions, personal ratings, photos, and customizable categories. Your memories deserve to be more than just map pins — keep them alive with full, organized logs.  
<img src="https://raw.githubusercontent.com/seanmorley15/AdventureLog/refs/heads/main/brand/screenshots/details.png" alt="Detailed Adventure Logs" style="max-width:100%; margin-top:10px;" />  
:::

::: details 🗺️ **Interactive World Map**  
Track every destination you’ve visited or plan to visit with our beautifully detailed, interactive world map. Easily filter locations by visit status — visited or planned — and add new locations by simply clicking on the map. Watch your travel story unfold visually as your journey grows.  
<img src="https://raw.githubusercontent.com/seanmorley15/AdventureLog/refs/heads/main/brand/screenshots/map.png" alt="Interactive World Map" style="max-width:100%; margin-top:10px;" />  
<img src="https://raw.githubusercontent.com/seanmorley15/AdventureLog/refs/heads/development/brand/screenshots/map-satellite.png" alt="Interactive World Map" style="max-width:100%; margin-top:10px;" />  
:::

::: details ✈️ **Comprehensive Trip Planning**  
Organize your multi-day trips with detailed itineraries, including flight information, daily activities, collaborative notes, packing checklists, and handy resource links. Stay on top of your plans and ensure every adventure runs smoothly.  
<img src="https://raw.githubusercontent.com/seanmorley15/AdventureLog/refs/heads/main/brand/screenshots/itinerary.png" alt="Comprehensive Trip Planning" style="max-width:100%; margin-top:10px;" />  
:::

::: details 📊 **Travel Statistics Dashboard**  
Unlock insights into your travel habits and milestones through elegant, easy-to-understand analytics. Track total countries visited, regions explored, cities logged, and more. Visualize your world travels with ease and celebrate your achievements.
<img src="https://raw.githubusercontent.com/seanmorley15/AdventureLog/refs/heads/main/brand/screenshots/dashboard.png" alt="Travel Statistics Dashboard" style="max-width:100%; margin-top:10px;" />  
:::

::: details ✏️ **Edit & Customize Locations**  
Make quick updates or deep customizations to any location using a clean and intuitive editing interface. Add photos, update notes, adjust dates, and more—keeping your records accurate and personal.  
<img src="https://raw.githubusercontent.com/seanmorley15/AdventureLog/refs/heads/main/brand/screenshots/edit.png" alt="Edit Location Modal" style="max-width:100%; margin-top:10px;" />  
:::

::: details 🌍 **Countries & Regions Explorer**  
Explore and manage the countries you’ve visited or plan to visit with an organized list, filtering by visit status. Dive deeper into each country’s regions, complete with interactive maps to help you visually select and track your regional travels.  
<img src="https://raw.githubusercontent.com/seanmorley15/AdventureLog/refs/heads/main/brand/screenshots/countries.png" alt="Countries List" style="max-width:100%; margin-top:10px;" />  
<img src="https://raw.githubusercontent.com/seanmorley15/AdventureLog/refs/heads/main/brand/screenshots/regions.png" alt="Regions Explorer" style="max-width:100%; margin-top:10px;" />  
:::

## 💬 What People Are Saying

::: details ✈️ **XDA Travel Week Reviews**

> “I stumbled upon AdventureLog. It's an open-source, self-hosted travel planner that's completely free to use and has a bunch of cool features that make it a treat to plan, organize, and log your journey across the world. Safe to say, it's become a mainstay in Docker for me.”
>
> — _Sumukh Rao, Senior Author at XDA_

[Article Link](https://www.xda-developers.com/i-self-hosted-this-app-to-plan-itinerary-when-traveling/)

:::

::: details 🧳 **Rich Edmonds, XDA**

**Overall Ranking: #1**

> “The most important part of travelling in this socially connected world is to log everything and showcase all of your adventures. AdventureLog is aptly named, as it allows you to do just that. It just so happens to be one of the best apps for the job and can be fully self-hosted at home.”
>
> — _Rich Edmonds, Lead PC Hardware Editor at XDA_

[Article Link](https://www.xda-developers.com/these-self-hosted-apps-are-perfect-for-those-on-the-go/)

:::

::: details 📆 **Open Source Daily**

> “Your travel memories are your personal treasures—don’t let them be held hostage by closed platforms, hidden fees, or privacy risks. AdventureLog represents a new era of travel tracking: open, private, comprehensive, and truly yours. Whether you’re a casual traveler, digital nomad, family vacation planner, or anyone who values their adventures, AdventureLog offers a compelling alternative that puts you back in control.”
>
> — _Open Source Daily_

[Article Link](https://opensourcedaily.blog/adventurelog-private-open-source-travel-tracking-trip-planning/)

:::

::: details 📱 **Android Authority**

> "AdventureLog behaves more like a super-charged travel journal than yet another travel app.”
>
> — _Dhruv Bhutani, Android Authority_

[Article Link](https://www.androidauthority.com/self-hosted-travel-app-3572353/)

:::

## 🏗️ Built With Excellence

<div class="tech-stack">

<div class="tech-card">

### **Frontend Excellence**

- 🎨 **SvelteKit** - Lightning-fast, modern web framework
- 💨 **TailwindCSS** - Utility-first styling for beautiful designs
- 🎭 **DaisyUI** - Beautiful, accessible component library
- 🗺️ **MapLibre** - Interactive, customizable mapping

</div>

<div class="tech-card">

### **Backend Power**

- 🐍 **Django** - Robust, scalable web framework
- 🗺️ **PostGIS** - Advanced geospatial database capabilities
- 🔌 **Django REST** - Modern API architecture
- 🔐 **AllAuth** - Comprehensive authentication system

</div>

</div>

## 🌟 Join the Adventure

<div class="community-stats">

<div class="community-card">

### 🎯 **Active Development**

Regular updates, new features, and community-driven improvements keep AdventureLog at the forefront of travel technology.

</div>

<div class="community-card">

### 💬 **Thriving Community**

Join thousands of travelers sharing tips, contributing code, and building the future of travel documentation together.

</div>

<div class="community-card">

### 🚀 **Open Source Freedom**

GPL 3.0 licensed, fully transparent, and built for the community. By travelers, for travelers.

</div>

</div>

## 💖 Support the Project

AdventureLog is lovingly maintained by passionate developers and supported by amazing users like you:

- ⭐ [Star us on GitHub](https://github.com/seanmorley15/AdventureLog)
- 💬 [Join our Discord community](https://discord.gg/wRbQ9Egr8C)
- 💖 [Sponsor The Project](https://seanmorley.com/sponsor) to help us keep improving AdventureLog
- 🐛 [Report bugs & request features](https://github.com/seanmorley15/AdventureLog/issues)

---

<div class="footer-cta">

### Ready to Transform Your Travel Experience?

Stop letting amazing adventures fade from memory. Start documenting, planning, and sharing your travel story today.

[**🚀 Get Started Now**](/docs/install/getting_started) • [**📱 Try the Demo**](https://demo.adventurelog.app) • [**📚 Read the Docs**](/docs/intro/adventurelog_overview)

</div>

<style>
.why-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.5rem;
  margin: 2rem 0;
}

.why-card {
  padding: 1.5rem;
  border-radius: 12px;
  border: 1px solid var(--vp-c-border);
  background: var(--vp-c-bg-soft);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.why-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
}

.why-card h3 {
  margin-bottom: 0.75rem;
  color: var(--vp-c-text-1);
}

.tech-stack {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1.5rem;
  margin: 2rem 0;
}

.tech-card {
  padding: 1.5rem;
  border-radius: 12px;
  border: 1px solid var(--vp-c-border);
  background: var(--vp-c-bg-soft);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.tech-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
}

.tech-card h3 {
  margin-bottom: 1rem;
  color: var(--vp-c-text-1);
}

.community-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.5rem;
  margin: 2rem 0;
}

.community-card {
  padding: 1.5rem;
  border-radius: 12px;
  border: 1px solid var(--vp-c-border);
  background: var(--vp-c-bg-soft);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.community-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
}

.community-card h3 {
  margin-bottom: 0.75rem;
  color: var(--vp-c-text-1);
}

.footer-cta {
  text-align: center;
  padding: 3rem 2rem;
  margin: 3rem 0;
  border-radius: 12px;
  background: linear-gradient(135deg, var(--vp-c-brand-soft) 0%, var(--vp-c-brand-softer) 100%);
  border: 1px solid var(--vp-c-brand-soft);
}

.footer-cta h3 {
  margin-bottom: 1rem;
  color: var(--vp-c-brand-dark);
}

.footer-cta p {
  margin-bottom: 2rem;
  font-size: 1.1rem;
  opacity: 0.8;
}

details img {
  border-radius: 12px;
}
</style>
