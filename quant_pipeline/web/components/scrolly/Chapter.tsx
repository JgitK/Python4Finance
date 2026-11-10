/**
 * Chapter: the heading block and the section of one chapter.
 *
 *   <Chapter id="ch-05" number={5} title={<>Ten thousand <em>portfolios</em></>} intro="...">
 *     <Scrolly ...>...</Scrolly>
 *   </Chapter>
 *
 * The `title` can hold one <em> word, which shows in italic tan.
 */

import type { ReactNode } from "react";

export interface ChapterProps {
  id: string;
  number: number;
  title: ReactNode;
  intro?: ReactNode;
  children: ReactNode;
}

export function Chapter({ id, number, title, intro, children }: ChapterProps) {
  return (
    <section id={id} className="chapter" aria-labelledby={`${id}-title`}>
      <div className="da-container">
        <header className="chapter-head">
          <span className="eyebrow">
            <span className="pixel-check" />
            Chapter {number}
          </span>
          <h2 id={`${id}-title`} className="da-h2">
            {title}
          </h2>
          {intro ? <p className="chapter-intro">{intro}</p> : null}
        </header>
        {children}
      </div>
    </section>
  );
}
