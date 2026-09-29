import { Link, useParams, useSearchParams } from 'react-router-dom';
import Sheet from '../components/Sheet';
import Toolbar from '../components/Toolbar';
import { bookIndex, findChart } from '../lib/charts';

export default function ChartPage() {
  const { id = '' } = useParams();
  const [search] = useSearchParams();
  // ?fit=0 renders the reference layout regardless of page length (used by the parity test).
  const fit = search.get('fit') !== '0';
  const chart = findChart(id);
  if (!chart) {
    return (
      <>
        <Toolbar />
        <main className="sheet index">
          <h1>Not in the book</h1>
          <p>
            No chart with id <code>{id}</code>. <Link to="/">Back to the index.</Link>
          </p>
        </main>
      </>
    );
  }
  return (
    <>
      <Toolbar current={chart.title} />
      <Sheet chart={chart} index={bookIndex(chart)} fit={fit} />
    </>
  );
}
