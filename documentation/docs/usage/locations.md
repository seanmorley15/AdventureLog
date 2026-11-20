# Locations and Visits

A **location** is a place: somewhere you've been, or somewhere you want to go. Locations are the building blocks of AdventureLog. Everything else, from trips to the world map, is made of them.

<AppShot name="locations" />

## What a location holds

Open a location to see its own page, with tabs for an overview, its visits, a map, and its photos and files.

<AppShot name="location" />

| On a location | What it is |
| ---------- | ---------- |
| **Visits** | The dates you were there, with notes. Add one for each time you went. |
| **Category** | One group per location, such as hiking, museums, or restaurants. Create your own with **Manage Categories**. |
| **Tags** | Any number of free-form labels, such as the cuisine at a restaurant. |
| **Rating** | Your own score out of five. |
| **Photos** | Uploaded from your device, or picked from [Immich](../configuration/immich_integration.md) when that integration is on. |
| **Attachments** | Files that belong with the location, such as a ticket, a brochure, or a map. |
| **Trails** | A route linked to the location, either as a link to another site or from [Wanderer](../configuration/wanderer_integration.md), which adds distance and elevation. |
| **Activities** | What you did on a visit, such as a hike or a ride, with time, distance, and a GPX track. Enter them by hand or import them from [Strava](../configuration/strava_integration.md) or [Endurain](../configuration/endurain_integration.md). |

## Visited or planned

AdventureLog works this out from a location's visits:

- A location with at least one visit in the past is **visited**.
- A location with no visits, or only visits in the future, is **planned**.

So to plan ahead, add a visit with a future date. When the day comes, the location becomes visited by itself.

**Add Today** in the visits menu records a visit for the current day in one click.

## Adding a location

Choose **Add New Location** and search for the location, or drop a marker on the map. AdventureLog looks up the city, region, and country in the background, so the location is saved right away and its region fills in a moment later.

While you type, AdventureLog checks for a location you already have with a similar name, address, or nearby coordinates. If it finds one it asks **Did you mean …?** and offers to open the existing location instead of creating a duplicate.

## Finding locations again

The Locations page lists everything you've saved. The sidebar narrows it down:

- **Categories** to show one or more groups.
- **Status** to show visited or not visited locations only.
- **Include Collection Locations** to also show locations that belong to a trip or folder.
- **Sort** by name, date, rating, or when a location was last updated.

For a search across everything in your account, use the search box in the top bar.

## Sharing a location

A location is private unless you make it public. Public locations can be seen by anyone with the link, and appear on your profile if your profile is visible. See [Sharing and Privacy](sharing.md).
