<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This app uses Next.js 16.2.4. This version has breaking changes: APIs,
conventions and file structure can differ from your training data. Read
the relevant guide in `node_modules/next/dist/docs/` before you write
code. Obey the deprecation notices.
<!-- END:nextjs-agent-rules -->

# Rules for this app

- Read `../docs/web_plan.md` first. It is the brief.
- React owns the DOM. D3 calculates, and D3 owns only the inside of an
  `<svg>` or a `<canvas>` through a ref.
- A chapter reads the store (`lib/store.tsx`). It never fetches data.
- Edit only the files of your own row in the plan.
- `npm run build`, `npx vitest run` and `npx tsc --noEmit` must pass.
