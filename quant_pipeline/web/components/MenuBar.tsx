import { FixtureBadge } from "@/components/ui";

const LINKS = [
  ["#ch-01", "Pick"],
  ["#ch-02", "Timing"],
  ["#ch-03", "Risk"],
  ["#ch-04", "Together"],
  ["#ch-05", "Frontier"],
  ["#ch-06", "Money"],
  ["#ch-07", "Trust"],
] as const;

/** The slim menu bar at the top of the page. */
export function MenuBar() {
  return (
    <div className="da-container menubar-wrap">
      <nav className="da-menubar" aria-label="Chapters">
        <a className="da-menu-item bold" href="#ch-00">
          markowitz.walk
        </a>
        {LINKS.map(([href, label]) => (
          <a key={href} className="da-menu-item hide-narrow" href={href}>
            {label}
          </a>
        ))}
        <span className="da-menu-clock">
          <FixtureBadge />
        </span>
      </nav>
    </div>
  );
}
