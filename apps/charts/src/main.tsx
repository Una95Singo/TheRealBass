import '@fontsource/architects-daughter';
import '@fontsource/nunito-sans/400.css';
import '@fontsource/nunito-sans/700.css';
import './styles/sheet.css';
import './styles/app.css';

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import ChartPage from './pages/ChartPage';
import IndexPage from './pages/IndexPage';
import PrintPage from './pages/PrintPage';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<IndexPage />} />
        <Route path="/chart/:id" element={<ChartPage />} />
        <Route path="/print" element={<PrintPage />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>,
);
