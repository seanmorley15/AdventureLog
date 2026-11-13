# The Map

The Map page shows every location you've saved on one interactive map, whether you've been there or are still planning to go. Zoom out and nearby locations group into numbered clusters; zoom in and they separate.

<AppShot name="map" />

## Choosing what the map shows

The **Map Controls** panel filters the map:

- **Stats** counts your locations, and how many are visited and planned.
- **Categories** shows only the groups you tick.
- **Display Options** switches layers on and off:
  - **Visited** and **Planned** locations
  - **Visited Regions** and **Visited Cities** from [World Travel](world_travel.md)
  - **Photos**, which shows pins where your photos were taken
  - **Activities**, which draws the GPX tracks of your activities

## Searching from the map

The search panel at the top of the map has three modes:

| Mode | What it does |
| ---- | ------------ |
| **My** | Searches the locations you've already saved. |
| **Places** | Searches for a new place to add. Select a result to see its details, then add it quickly or with more details. |
| **Nearby** | Finds places around the area you're looking at. Pan the map, then choose **Search this area**. |

You can also click anywhere on the map to drop a marker and add a location there.

## Map styles

The style menu in the corner of the map switches the basemap. The styles on offer depend on how the server is set up:

- Out of the box, the default is OpenFreeMap, light or dark to match your theme.
- A server with a CARTO key gets more styles, including a 3D terrain view. See `PUBLIC_CARTO_BASEMAP_API_KEY` in [Environment Variables](../configuration/environment_variables.md#integrations).
- [Google Maps](../configuration/google_maps_integration.md) can be turned on for place search and map details.

## Maps elsewhere in the app

Every trip has its own map of the route, each location has a map on its page, and World Travel has a map of the countries and regions you've been to.
