# Public Access

By default, anyone can see what your users choose to make public, even without an account: public and unlisted collection stories, public locations, public profiles, and guest links to a collection.

To make the server private to its own users, so that nothing can be seen without signing in, set `ALLOW_PUBLIC_ACCESS` to `False` under the server service in your `docker-compose.yml` (or in your `.env` file):

```yaml
environment:
  - ALLOW_PUBLIC_ACCESS=False
```

Restart the server for the change to take effect. Turning it back to `True` (the default) restores public access without changing anything users have set.

## What changes when public access is off

| | `ALLOW_PUBLIC_ACCESS=True` (default) | `ALLOW_PUBLIC_ACCESS=False` |
| --- | --- | --- |
| Public and unlisted collection stories | Anyone can read them | Only signed-in users can read them. New collections can't be made public or unlisted. |
| Collections shown to "Everyone signed in" | Signed-in users | Signed-in users |
| Public locations, lodging and transportation | Anyone | Signed-in users |
| Public profiles | Anyone | Signed-in users. The **Public** option is unavailable in settings. |
| Guest links | Open the collection without an account | Stop working. New guest links can't be created. |
| Photos and files of all of the above | Follow the same rules | Follow the same rules |

Signed-out visitors get a "not found" response instead of the content. Collection members, invited users and the owners themselves are not affected: sharing a collection with people who have an account works the same either way.

Nothing is deleted or changed in the database. Collections that were already public keep that setting, and are simply shown to signed-in users only while public access is off.

## Who can see what

These settings are available whether public access is on or off:

- **Profiles** can be **Private** (only you; nobody can find you to share a collection), **Signed-in users** (everyone signed in to the server can see your profile and invite you to collections) or **Public**. Choose it under **Settings → Profile**.
- **Collections** can be **Private**, **Everyone signed in**, **Unlisted** (anyone with the link) or **Public**. Choose it on the **Story** tab of a collection's share sheet. The owner decides which parts of the story are shown (costs, reservations, attachments and so on) in every case except Private.

Related: [Disable Registration](disable_registration.md) stops new sign-ups. Together, the two settings make an invitation-only, signed-in-only server.
