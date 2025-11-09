# Bucket List API

## Overview
The Bucket List feature allows users to track travel goals and experiences they want to complete.

## Endpoints

### List Bucket Items
```
GET /api/bucketlist/items/
```
Returns a list of bucket list items for the authenticated user and public items.

**Query Parameters:**
- `status` (optional): Filter by status (`planned`, `in_progress`, `completed`)
- `page` (optional): Page number for pagination

**Response:**
```json
[
  {
    "id": "uuid",
    "user": "user-uuid",
    "title": "Climb Mount Kilimanjaro",
    "description": "Summit Africa's highest peak",
    "tags": ["hiking", "adventure", "africa"],
    "status": "planned",
    "location": "location-uuid-or-null",
    "notes": "Best time: June-October",
    "is_public": false,
    "created_at": "2025-10-30T10:00:00Z",
    "updated_at": "2025-10-30T10:00:00Z"
  }
]
```

### Create Bucket Item
```
POST /api/bucketlist/items/
```
Creates a new bucket list item (user is automatically set from auth).

**Request Body:**
```json
{
  "title": "Visit Machu Picchu",
  "description": "Explore the ancient Incan city",
  "tags": ["peru", "history", "unesco"],
  "status": "planned",
  "location": null,
  "notes": "Consider booking guide in advance",
  "is_public": false
}
```

### Retrieve Bucket Item
```
GET /api/bucketlist/items/{id}/
```
Get details of a specific bucket list item.

### Update Bucket Item
```
PUT /api/bucketlist/items/{id}/
PATCH /api/bucketlist/items/{id}/
```
Update an existing bucket list item (only owner can modify).

**Request Body (PATCH example):**
```json
{
  "status": "completed",
  "notes": "Completed in October 2025!"
}
```

### Delete Bucket Item
```
DELETE /api/bucketlist/items/{id}/
```
Delete a bucket list item (only owner can delete).

## Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Auto | Unique identifier |
| `user` | UUID | Auto | Owner (set from authentication) |
| `title` | String | Yes | Item title (max 200 chars) |
| `description` | Text | No | Detailed description |
| `tags` | Array[String] | No | Tags for categorization |
| `status` | String | No | Status: `planned`, `in_progress`, `completed` (default: `planned`) |
| `location` | UUID | No | Optional link to an existing Location |
| `notes` | Text | No | Additional notes |
| `is_public` | Boolean | No | Public visibility (default: false) |
| `created_at` | DateTime | Auto | Creation timestamp |
| `updated_at` | DateTime | Auto | Last update timestamp |

## Permissions

- **List**: Authenticated users see their own items + public items. Unauthenticated users see only public items.
- **Create**: Requires authentication.
- **Update/Delete**: Only the owner can modify or delete their items.

## Future Enhancements

- Attach images/files via existing `ContentImage` and `ContentAttachment` models (GenericRelation already configured)
- Link to Collections or Trips
- Progress tracking dashboard widget
- Public bucket list sharing URLs
