import { Link } from 'react-router-dom';

export default function Toolbar({ current }: { current?: string }) {
  return (
    <nav className="toolbar" aria-label="Low Book">
      <Link to="/">Low Book</Link>
      {current && <span className="crumb">/ {current}</span>}
      <span className="spacer" />
      <Link to="/print">Print all</Link>
      <button type="button" onClick={() => window.print()}>
        Print
      </button>
    </nav>
  );
}
