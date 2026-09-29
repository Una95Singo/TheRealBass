import type { Chart } from '@lowbook/chart-core';
import { Link } from 'react-router-dom';

export default function BookIndex({
  charts,
  title = 'Low Book',
}: {
  charts: Chart[];
  title?: string;
}) {
  return (
    <main className="sheet index" id="index">
      <h1>{title}</h1>
      <ol>
        {charts.map((c) => (
          <li key={c.id}>
            <Link to={`/chart/${c.id}`}>{c.title}</Link> <sub>{c.artist}</sub>
          </li>
        ))}
      </ol>
      <div className="legend">
        Confidence marks on bar counts, from cross-checking sources: ● three sources agree &nbsp; ◐
        two agree or one gives timing &nbsp; ○ estimate — count it against the record.
      </div>
    </main>
  );
}
