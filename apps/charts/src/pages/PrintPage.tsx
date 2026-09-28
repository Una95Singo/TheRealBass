import BookIndex from '../components/BookIndex';
import Sheet from '../components/Sheet';
import Toolbar from '../components/Toolbar';
import { charts } from '../lib/charts';

/** The whole book, one song per page, ready for the print dialog. */
export default function PrintPage() {
  return (
    <>
      <Toolbar current="Print all" />
      <BookIndex charts={charts} />
      {charts.map((c, i) => (
        <Sheet key={c.id} chart={c} index={i + 1} />
      ))}
    </>
  );
}
