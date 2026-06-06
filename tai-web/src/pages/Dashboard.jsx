import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Package, BookOpen, FileText, MessageSquare, ArrowRight } from 'lucide-react';
import { getProducts, getKnowledge, getQuotes, getSessions } from '../api/client';
import { Card, Spinner } from '../components/UI';

function StatCard({ icon: Icon, label, value, to, color = 'var(--accent)' }) {
  return (
    <Link to={to}>
      <Card style={{ display: 'flex', alignItems: 'center', gap: 16, cursor: 'pointer', transition: 'border-color .15s' }}>
        <div style={{ width: 44, height: 44, borderRadius: 10, background: 'var(--surface2)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
          <Icon size={20} color={color} />
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 24, fontWeight: 800 }}>{value ?? '—'}</div>
          <div style={{ fontSize: 12, color: 'var(--text-dim)' }}>{label}</div>
        </div>
        <ArrowRight size={16} color="var(--text-dim)" />
      </Card>
    </Link>
  );
}

export default function Dashboard() {
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.allSettled([
      getProducts({ limit: 1 }),
      getKnowledge({ limit: 1 }),
      getQuotes({ limit: 1 }),
      getSessions({ limit: 1 }),
    ]).then(([p, k, q, s]) => {
      // We just need counts; fetch with larger limit to count
      Promise.allSettled([
        getProducts({ limit: 200 }),
        getKnowledge({ limit: 200 }),
        getQuotes({ limit: 200 }),
        getSessions({ limit: 200 }),
      ]).then(([pp, kk, qq, ss]) => {
        setStats({
          products: pp.status === 'fulfilled' ? pp.value.data.length : '?',
          knowledge: kk.status === 'fulfilled' ? kk.value.data.length : '?',
          quotes: qq.status === 'fulfilled' ? qq.value.data.length : '?',
          sessions: ss.status === 'fulfilled' ? ss.value.data.length : '?',
        });
        setLoading(false);
      });
    });
  }, []);

  if (loading) return <Spinner />;

  return (
    <div>
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 22, fontWeight: 800 }}>Dashboard</h1>
        <p style={{ color: 'var(--text-dim)', marginTop: 4 }}>The Blue Red Admin Panel</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(240px,1fr))', gap: 16 }}>
        <StatCard icon={Package} label="Toplam Ürün" value={stats.products} to="/products" color="var(--accent)" />
        <StatCard icon={BookOpen} label="Bilgi Kaydı" value={stats.knowledge} to="/knowledge" color="var(--green)" />
        <StatCard icon={FileText} label="Teklif" value={stats.quotes} to="/quotes" color="var(--yellow)" />
        <StatCard icon={MessageSquare} label="Oturum" value={stats.sessions} to="/sessions" color="var(--red)" />
      </div>

      <div style={{ marginTop: 32, padding: '16px 20px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10 }}>
        <div style={{ fontSize: 12, color: 'var(--text-dim)', fontWeight: 600, marginBottom: 6 }}>BACKEND BAĞLANTISI</div>
        <div style={{ fontSize: 13 }}>
          <span style={{ color: 'var(--green)' }}>●</span>{' '}
          {import.meta.env.VITE_API_URL || 'http://localhost:8000'}
        </div>
      </div>
    </div>
  );
}
