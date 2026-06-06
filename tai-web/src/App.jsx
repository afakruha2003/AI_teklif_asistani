import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Products from './pages/Products';
import Knowledge from './pages/Knowledge';
import Quotes from './pages/Quotes';
import Sessions from './pages/Sessions';

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/products" element={<Products />} />
          <Route path="/knowledge" element={<Knowledge />} />
          <Route path="/quotes" element={<Quotes />} />
          <Route path="/sessions" element={<Sessions />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
