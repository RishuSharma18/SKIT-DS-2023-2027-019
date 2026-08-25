# Slot Grid Responsive Layout Specifications

Grid breakdown rules for 2-wheeler, car, and heavy vehicle slot cells.

## Breakpoint Matrix
- **Mobile (< 640px)**: 2 columns grid (`grid-cols-2 gap-2`)
- **Tablet (640px - 1024px)**: 4 columns grid (`grid-cols-4 gap-3`)
- **Desktop (> 1024px)**: 6 columns grid (`grid-cols-6 gap-4`)

## Card Geometry
- Height: `h-28`
- Rounded: `rounded-xl`
- Transition: `transition-all duration-200 hover:scale-[1.02]`
- Active border for selected slot: `ring-2 ring-blue-500`
