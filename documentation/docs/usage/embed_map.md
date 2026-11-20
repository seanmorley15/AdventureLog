# Embed Your Map

Show a map of your public locations on your own website, blog, or portfolio. The map is a small page you place in an `<iframe>`. It updates by itself as you add places.

## Get the code

1. Set your profile to **Public** in **Settings**. Embedding is not available for profiles that are private or visible only to signed-in users.
2. Open your profile and choose the **Map** tab.
3. Open **Embed this map on your website**, pick a height, whether the profile panel starts open or collapsed, and a theme, and select **Copy**.
4. Paste the code into your page.

```html
<iframe
  src="https://your-adventurelog.example/embed/profile/yourname?theme=light"
  width="100%"
  height="450"
  style="border:0;border-radius:12px"
  loading="lazy"
  title="yourname on AdventureLog"
></iframe>
```

## Options

Options go on the end of the address.

| Option             | Values                      | Default      | What it does                                                    |
| ------------------ | --------------------------- | ------------ | --------------------------------------------------------------- |
| `profile`          | `hide`                      | open         | `hide` starts with the profile panel collapsed to a small button. Visitors can still open it. |
| `theme`            | `light`, `dark`, any theme  | light        | The colors of the map frame and the panel.                      |

With the profile panel, visitors see your name, picture, rank and totals, and a link to your full profile. The panel floats over the map and can be folded away. On small frames it always starts folded.

Example, dark theme with the panel collapsed: `/embed/profile/yourname?theme=dark&profile=hide`

## What visitors see

- Only your **public** locations that have coordinates. Private locations never appear.
- A pin opens that location's public page in a new tab.
- A **Powered by AdventureLog** badge that links to [adventurelog.app](https://adventurelog.app).

The embed is loaded without anyone's sign-in. It shows what a signed-out visitor could see, even when the person looking at it is signed in to your server.

## For server administrators

- The embed is served at `/embed/profile/<username>` on your AdventureLog address. It is the only page that other websites may frame; every other page keeps its normal behavior.
- If you run a reverse proxy that adds `X-Frame-Options` or a `frame-ancestors` policy, exclude `/embed/` from it, or the embed will be blocked.
- With `ALLOW_PUBLIC_ACCESS=False` the embed does not load for people who are not signed in. See [Public Access](../configuration/public_access.md).
