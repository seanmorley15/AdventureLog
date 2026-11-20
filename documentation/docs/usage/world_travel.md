# World Travel

World Travel tracks the countries, regions, and cities you've been to over your lifetime, separately from the individual locations you log.

<AppShot name="world" />

## Countries, regions, and cities

The data has three levels:

- A **country**, such as France.
- A **region** inside a country, such as a state, province, or department.
- A **city** inside a region.

A country counts as visited as soon as you mark one of its regions. Each country shows how many of its regions you've covered, so you can see at a glance where you've only passed through and where you've been all over.

A country is shown as:

- **Complete** when you've visited every region in it.
- **Partial** when you've visited some of its regions.
- **Not Visited** when you haven't marked any.

## Browsing the list

- **Search** finds a country by name.
- **Filter by** All, Complete, Partial, or Not Visited.
- **Filter by Region** narrows the list to one part of the world, such as Northern Europe or Polynesia.
- **Show Map** puts your visited countries on a world map.
- **Show Globe Spin** shows them on a spinning globe.

The sidebar keeps count of how many countries you've visited, how many remain, and your overall progress.

## How it connects to your locations

When you save a location, AdventureLog works out which country, region, and city it's in. Visited regions and cities can also be shown as layers on [the Map](map.md), and the dashboard counts your visited countries.

## Territories

Some places are listed twice in the world data: as a country of their own and as a region of a larger country. Puerto Rico is both a country and a region of the United States; Guadeloupe is both a country and a region of France. AdventureLog treats each pair as one place:

- New locations are filed under the territory's own country, such as Puerto Rico.
- You mark it visited on the territory's own page. The matching region under the larger country shows as visited too, and opening it takes you to the territory.
- Statistics count the visit once, for the territory, not again for the larger country.

This covers the US territories, the French overseas territories, Hong Kong and Macau, Svalbard, and others like them.

## If the country list is empty

The country and region data is downloaded when the server first starts. If the list is empty, the server skipped that step or hasn't finished it. A server admin can run the import by hand; see [Management Commands](../configuration/management_commands.md#world-data).
