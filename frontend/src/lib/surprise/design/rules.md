# Yvette Surprise Card - Design & Implementation Rules

## Spacing Grid (Mandatory)

- Use: 4/8/12/16/24/32px only
- Card padding: 24px (6 tokens)
- Gap between elements: 16px (4 tokens)
- Section padding: 32px (8 tokens)

## Typography Hierarchy

- **Spanish Title (ES)**: 36px (3xl), Playfair Display, semi-bold, primary color
- **English Subtitle (EN)**: 18px (lg), Inter, normal weight, muted (neutral-600)
- **Body Text**: 16px (base), Inter, normal, neutral-700
- **Labels**: 14px (sm), Inter, medium, neutral-600

## Card Specifications

- Max-width: 680px
- Image aspect ratio: 16:10 (1.6:1)
- Border radius: 24px (2xl)
- Background: gradient (white → #fffbf7)
- Shadow: card-shadow (0 4px 20px rgba(28, 25, 23, 0.08))
- Border: 1px solid rgba(28, 25, 23, 0.05)

## Locked State Behavior

- Image: 20px blur filter
- Overlay: dark gradient (0.6 → 0.85 opacity)
- Lock icon: center, 64px size, gold color
- Text: "Sorpresa bloqueada" in white, 24px
- Button: Unlock CTA, prominent, gold accent

## Unlocked State Behavior

- Image: sharp (blur: 0)
- Overlay: removed/fade out over 500ms
- Buttons appear: "Navegar / Navigate" + "Siguiente sorpresa / Next"
- Progress: updates to show X/6
- Animation: fade-in + subtle slide-up

## Button Specifications

- **Primary (Unlock)**:
  - Background: gold (#eab308)
  - Text: dark neutral (#1c1917)
  - Padding: 12px 24px
  - Height: 44px min
  - Border radius: 9999px
  - Hover: gold-600 (#ca8a04)
- **Secondary (Navigate)**:
  - Background: transparent
  - Border: 2px solid primary (#e04d75)
  - Text: primary
  - Padding: 12px 24px
  - Height: 44px
  - Hover: light primary bg

## Accessibility (AA Compliance)

- All text: minimum 4.5:1 contrast ratio
- Focus rings: 2px solid gold, 2px offset
- Touch targets: 44px minimum height
- Keyboard navigation: full support (Tab/Enter/Escape)
- Images: alt text in all img tags
- Color not sole differentiator

## Animation Timing

- Fade/reveal: 500ms, easing: cubic-bezier(0.16, 1, 0.3, 1)
- Confetti burst: 3000ms total
- Button hover: 150ms, easing: ease-out
- Blur removal: 300ms smooth transition

## Performance

- Images: WebP format, max 800px width (2x display)
- No heavy libs (only canvas-confetti for confetti)
- Lazy load below-the-fold content
- Cache confetti canvas after first render

## Mobile-First

- Base: mobile fullscreen
- Tablet (768px+): max-width resets
- Desktop (1024px+): centered card layout
- Touch-friendly padding: 16px margins on mobile
