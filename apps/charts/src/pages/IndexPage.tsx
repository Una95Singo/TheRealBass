import BookIndex from '../components/BookIndex';
import Toolbar from '../components/Toolbar';
import { charts } from '../lib/charts';

export default function IndexPage() {
  return (
    <>
      <Toolbar />
      <BookIndex charts={charts} />
    </>
  );
}
