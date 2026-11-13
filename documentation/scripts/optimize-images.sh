#!/usr/bin/env bash
# Builds the optimized images the docs site serves from documentation/public.
# The output is committed, so the deploy host never needs ImageMagick.
#
#   ./scripts/optimize-images.sh photos            # travel photos, OG card, icons
#   ./scripts/optimize-images.sh shots <dir>       # app screenshots from <dir>/{light,dark}/*.png
#
# Screenshots come from scripts/capture-screenshots.mjs (real app, demo data).
# After adding one, list it in .vitepress/screenshots.ts.
set -euo pipefail

if command -v magick >/dev/null 2>&1 && magick -version 2>/dev/null | grep -q "ImageMagick 7"; then
  im=(magick)
elif command -v convert >/dev/null 2>&1; then
  im=(convert)
else
  echo "ImageMagick (with WebP and AVIF support) is required." >&2
  exit 1
fi

# ImageMagick 6 sometimes aborts a slow AVIF encode with "time limit exceeded".
export MAGICK_TIME_LIMIT="${MAGICK_TIME_LIMIT:-3600}"

here="$(cd "$(dirname "$0")/.." && pwd)"
repo="$here/.."
public="$here/public"
mode="${1:-}"

encode() { # src, width, out-basename, avif-quality, webp-quality
  "${im[@]}" "$1" -strip -resize "${2}x>" -quality "$5" "$3-$2.webp"
  "${im[@]}" "$1" -strip -resize "${2}x>" -quality "$4" "$3-$2.avif"
}

case "$mode" in
  shots)
    src="${2:?usage: optimize-images.sh shots <dir>}"
    mkdir -p "$public/screenshots"
    for theme in light dark; do
      for png in "$src/$theme"/*.png; do
        name="$(basename "$png" .png)"
        for w in 800 1440 2200; do
          encode "$png" "$w" "$public/screenshots/$name-$theme" 50 78
        done
        echo "screenshots/$name-$theme"
      done
    done
    ;;
  photos)
    mkdir -p "$public/photos" "$public/og"
    # The maintainer's own travel photos, shipped with the app as login backgrounds.
    bg="$repo/frontend/static/backgrounds"
    photo() { # source number, slug, aspect W, aspect H, gravity
      # Crop once at full size, then derive the smaller widths from that.
      tmp="$(mktemp --suffix=.png)"
      "${im[@]}" "$bg/adventurelog_showcase_$1.webp" -strip -resize "2400x$(( 2400 * $4 / $3 ))^" \
        -gravity "$5" -extent "2400x$(( 2400 * $4 / $3 ))" "$tmp"
      for w in 800 1600 2400; do
        "${im[@]}" "$tmp" -resize "${w}x" -quality 74 "$public/photos/$2-$w.webp"
        "${im[@]}" "$tmp" -resize "${w}x" -quality 52 "$public/photos/$2-$w.avif"
      done
      rm -f "$tmp"
      echo "photos/$2"
    }
    photo 3 philmont 16 7 center
    "${im[@]}" "$repo/brand/banner.png" -strip -resize 1260x630^ -gravity center -extent 1200x630 \
      -quality 84 -interlace Plane "$public/og/adventurelog.jpg"
    "${im[@]}" "$repo/brand/adventurelog.png" -strip -resize 180x180 "$public/apple-touch-icon.png"
    "${im[@]}" "$repo/brand/adventurelog.png" -strip -resize 192x192 "$public/icon-192.png"
    cp "$repo/brand/adventurelog.png" "$public/icon-512.png"
    echo "og + icons"
    ;;
  *)
    echo "usage: optimize-images.sh photos | shots <dir>" >&2
    exit 1
    ;;
esac
