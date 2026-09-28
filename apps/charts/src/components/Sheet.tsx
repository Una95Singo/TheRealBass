import { CONFIDENCE_MARK, chartToAbc, formLabel, type Chart } from '@lowbook/chart-core';
import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { firstLayout, fitsOnePage, layoutLabel, nextLayout, type Layout } from '../lib/fit';
import { renderMarkers } from '../lib/markers';
import { keyName } from '../lib/render';
import Staff from './Staff';

export interface SheetProps {
  chart: Chart;
  /** 1-based book position for the ABC X: field. */
  index?: number;
  /** Step the layout down until the sheet fits one page (default on). */
  fit?: boolean;
}

function verifyText(chart: Chart): string | null {
  const v = chart.verify;
  if (!v) return null;
  if (v.text) return v.text;
  const parts: string[] = [];
  if (v.agree.length) {
    const names =
      v.agree.length > 1 ? `${v.agree.slice(0, -1).join(', ')} and ${v.agree.at(-1)}` : v.agree[0]!;
    parts.push(`Sources: ${names} agree.`);
  }
  if (v.check.length) parts.push(`**Check:** ${v.check.join('; ')}.`);
  return parts.join(' ') || null;
}

/** Guard against a split that keeps toggling; more than this many attempts and we accept the overflow. */
const MAX_ATTEMPTS = 12;

export default function Sheet({ chart, index = 1, fit = true }: SheetProps) {
  const [layout, setLayout] = useState<Layout>(firstLayout);
  const [settled, setSettled] = useState(false);
  const attempts = useRef(0);
  const tried = useRef(new Set<string>());
  const page1 = useRef<HTMLElement>(null);
  const page2 = useRef<HTMLElement>(null);
  const rendered = useRef(0);

  // A new chart starts the search again.
  const prevChart = useRef(chart);
  useEffect(() => {
    if (prevChart.current === chart) return;
    prevChart.current = chart;
    setLayout(firstLayout());
    setSettled(false);
    attempts.current = 0;
    tried.current = new Set();
  }, [chart]);

  const blocks = useMemo(() => {
    if (layout.kind === 'single') {
      return [chartToAbc(chart, { barsPerLine: layout.barsPerLine, x: index })];
    }
    return [
      chartToAbc(chart, {
        barsPerLine: layout.barsPerLine,
        x: index,
        range: { from: 0, to: layout.at },
      }),
      chartToAbc(chart, {
        barsPerLine: layout.barsPerLine,
        x: index,
        range: { from: layout.at, to: chart.sections.length },
      }),
    ];
  }, [chart, index, layout]);

  const onRendered = useCallback(() => {
    rendered.current += 1;
    if (rendered.current < blocks.length) return;
    rendered.current = 0;
    if (!fit) {
      setSettled(true);
      return;
    }
    const over1 = !!page1.current && !fitsOnePage(page1.current.offsetHeight);
    const over2 = !!page2.current && !fitsOnePage(page2.current.offsetHeight);
    if (!over1 && !over2) {
      setSettled(true);
      return;
    }
    attempts.current += 1;
    tried.current.add(layoutLabel(layout));
    const next = nextLayout(layout, chart, { page1: over1, page2: over2 }, tried.current);
    if (!next || attempts.current > MAX_ATTEMPTS) {
      setSettled(true);
      return;
    }
    setLayout(next);
  }, [blocks.length, chart, fit, layout]);

  const footer = verifyText(chart);
  const pages = layout.kind === 'split' ? 2 : 1;
  const fitAttr = settled ? layoutLabel(layout) : 'pending';

  const header = (
    <header className="head">
      <div>
        <h1 className="title">{chart.title}</h1>
        <p className="artist">
          {chart.artist}
          {chart.year !== undefined && <>&nbsp;&nbsp;·&nbsp;&nbsp;{chart.year}</>}
          &nbsp;&nbsp;·&nbsp;&nbsp;bass
          {pages === 2 && <span className="pp"> &nbsp;·&nbsp; 2 pp.</span>}
        </p>
      </div>
      <div className="meta">
        <b>{chart.key.display}</b>
        {chart.key.relative && <> ({chart.key.relative})</>}
        <br />♩ = {chart.bpm} &nbsp; {chart.time}
        {chart.feel && (
          <>
            <br />
            {chart.feel}
          </>
        )}
      </div>
    </header>
  );

  const form = (
    <div className="form">
      {chart.form.map((f, j) => (
        <Fragment key={j}>
          <span>
            {formLabel(f)}
            <sub>{f.section}</sub>
            <span className="c">{CONFIDENCE_MARK[f.confidence]}</span>
          </span>
          {j < chart.form.length - 1 && <span className="arrow">›</span>}
        </Fragment>
      ))}
    </div>
  );

  const tail = (
    <>
      <section className="notes">
        <div>
          <h3>Bass notes</h3>
          <ul>
            {chart.notes.map((n, j) => (
              <li key={j}>{renderMarkers(n)}</li>
            ))}
          </ul>
        </div>
        <div>
          <h3>In numbers (key of {keyName(chart.key.abc)})</h3>
          <div className="numbers">{chart.numbers}</div>
        </div>
      </section>
      {footer && <p className="verify">{renderMarkers(footer)}</p>}
    </>
  );

  if (layout.kind === 'single') {
    return (
      <main
        ref={page1}
        className="sheet"
        id={chart.id}
        data-chart={chart.id}
        data-fit={fitAttr}
        data-pages={pages}
      >
        {header}
        {form}
        <Staff key={`${layout.barsPerLine}-single`} abc={blocks[0]!} onRendered={onRendered} />
        {tail}
      </main>
    );
  }

  return (
    <>
      <main
        ref={page1}
        className="sheet"
        id={chart.id}
        data-chart={chart.id}
        data-fit={fitAttr}
        data-pages={pages}
      >
        {header}
        {form}
        <Staff key={`${layoutLabel(layout)}-1`} abc={blocks[0]!} onRendered={onRendered} />
        <p className="turn">continues ›</p>
      </main>
      <main
        ref={page2}
        className="sheet continuation"
        id={`${chart.id}-2`}
        data-chart={chart.id}
        data-page="2"
      >
        <header className="cont">
          <span className="cont-title">{chart.title}</span>
          <span className="cont-meta">
            {chart.artist} &nbsp;·&nbsp; {chart.key.display} &nbsp;·&nbsp; ♩ = {chart.bpm}{' '}
            &nbsp;·&nbsp; p. 2 / 2
          </span>
        </header>
        <Staff key={`${layoutLabel(layout)}-2`} abc={blocks[1]!} onRendered={onRendered} />
        {tail}
      </main>
    </>
  );
}
