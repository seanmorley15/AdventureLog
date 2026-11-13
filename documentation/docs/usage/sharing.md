# Sharing and Privacy

Everything in AdventureLog is private until you choose to share it. You decide who can see each collection, each location, and your profile.

## Sharing a collection

The **Share** button on a collection opens one sheet for people, links, and visibility.

### Invite people

Invite another user on your server to a collection as:

- an **Editor**, who can change days, locations, notes, bookings, and files, or
- a **Viewer**, who can read the whole plan.

### Guest links

A **guest link** opens the private plan without an account. Give each link a label, an optional expiry date, and a role, and revoke it with one click when it's no longer needed.

### Comments and activity

Everyone on a trip can leave **comments** on the plan, reply to each other, and **@mention** someone to send them an email. The **Activity** feed shows who moved what, who joined, and when the trip dates changed.

## Travel stories

Any collection can be published as a **travel story**: a read-only page with its days, map, locations, photos, and bookings, made to send to friends and family.

Choose who can read the story:

| Visibility | Who can read it |
| ---------- | --------------- |
| **Private** | Only you and the people you've invited. |
| **Everyone signed in** | Any user signed in to your server. |
| **Unlisted** | Anyone with the link. |
| **Public** | Anyone. |

You also choose what the story shows. Costs, reservation numbers, exact lodging addresses, map pins, attachments, GPX tracks, note text, and checklist items each stay hidden until you turn them on, and you can hide any single note. **Preview** shows exactly what readers will see before you share the link.

## Public locations

A single location can be made public from its own page. Anyone who can read a location can copy it into their own account.

## Your profile

Your profile can be **Private**, visible to **Signed-in users**, or **Public**. A profile visible to signed-in users can be found and invited to collections without being public.

## For server administrators

- Set `ALLOW_PUBLIC_ACCESS=False` to keep everything behind sign-in, including public and unlisted stories, public locations, profiles, and guest links. See [Public Access](../configuration/public_access.md).
- To stop new sign-ups, see [Disable Registration](../configuration/disable_registration.md). To add people yourself, see [Invite a User](../guides/invite_user.md).
