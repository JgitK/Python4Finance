// The four rules of the pane (step 6) and the closing block under the chapter.

import s from "./trust.module.css";

export function Rules() {
  return (
    <ol className={s.rules} aria-label="The four rules">
      <li>
        <span>
          Markowitz is a <em>risk</em> tool.
          <small>It shows how stocks pull on each other. That part holds up.</small>
        </span>
      </li>
      <li>
        <span>
          Trust the covariance more than the return.
          <small>Risk is measured well from a few years. Expected return is not.</small>
        </span>
      </li>
      <li>
        <span>
          Spread across sectors.
          <small>Different businesses fall at different times.</small>
        </span>
      </li>
      <li>
        <span>
          Equal weight is hard to beat.
          <small>The simple split is a fair bar to clear before you trust a clever one.</small>
        </span>
      </li>
    </ol>
  );
}

export function Closing() {
  return (
    <div className={s.closing}>
      <h3>What this page did not show</h3>
      <ul>
        <li>
          <b>Survivorship bias.</b>{" "}The stocks are today&rsquo;s S&amp;P 500 members. Companies that fell out of the
          index are not here, so the past looks nicer than it was.
        </li>
        <li>
          <b>Sectors as of today.</b>{" "}A stock&rsquo;s sector is its current one, not the one it had at the time.
        </li>
        <li>
          <b>Overlapping windows.</b> The test windows share days. That makes the results look more solid than
          their count suggests.
        </li>
        <li>
          <b>No costs or taxes.</b> No commissions, no spread, no tax on gains, and no rebalancing.
        </li>
      </ul>
      <p className={s.disclaimer}>
        This is a learning tool, not investment advice. The money is pretend. Nothing here tells you what to buy.
      </p>
      <p className={s.sources}>
        Further reading: Markowitz, &ldquo;Portfolio Selection&rdquo; (1952) · Michaud, &ldquo;The Markowitz
        Optimization Enigma&rdquo; (1989) · DeMiguel, Garlappi and Uppal, &ldquo;Optimal Versus Naive
        Diversification&rdquo; (2009).
      </p>
    </div>
  );
}
