import { useEffect, useState, useCallback } from 'react';
import { RefreshCw, ChevronDown, ChevronRight } from 'lucide-react';
import { getQuotes, getQuote } from '../api/client';
import { PageHeader, Btn, Table, TD, Badge, Spinner, Card } from '../components/UI';

function statusColor(s) {
  return { draft: 'blue', sent: 'yellow', accepted: 'green', rejected: 'red' }[s] || 'gray';
}
function statusLabel(s) {
  return { draft: 'Taslak', sent: 'Gönderildi', accepted: 'Kabul', rejected: 'Reddedildi' }[s] || s;
}
function itemStatusColor(s) {
  return { active: 'green', replaced: 'yellow', removed: 'red' }[s] || 'gray';
}

function QuoteDetail({ quoteId, onClose }) {
  const [quote, setQuote] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    getQuote(quoteId).then(r => { setQuote(r.data); setLoading(false); });
  }, [quoteId]);

  useEffect(() => {
    load();
    // Poll every 4s to detect mobile mutations
    const t = setInterval(load, 4000);
    return () => clearInterval(t);
  }, [load]);

  if (loading && !quote) return <Spinner />;
  if (!quote) return null;

  const activeItems = (quote.items || []).filter(i => i.status === 'active');
  const total = activeItems.reduce((s, i) => s + i.quantity * i.unit_price_try * (1 - i.discount_pct / 100), 0);

  return (
    <div style={{ marginTop: 16, background: 'var(--surface2)', border: '1px solid var(--border)', borderRadius: 10, padding: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <span style={{ fontSize: 12, color: 'var(--text-dim)' }}>Teklif ID: </span>
          <span style={{ fontFamily: 'monospace', fontSize: 12 }}>{quote.id}</span>
          <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 2 }}>
            Son güncelleme: {new Date(quote.updated_at).toLocaleString('tr-TR')}
            <span style={{ marginLeft: 8, color: 'var(--accent)' }}>● canlı izleniyor</span>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <Btn variant="ghost" icon={RefreshCw} onClick={load} style={{ padding: '5px 10px' }} />
          <Btn variant="ghost" onClick={onClose}>Kapat</Btn>
        </div>
      </div>

      {quote.items?.length === 0 ? (
        <div style={{ color: 'var(--text-dim)', fontSize: 13, textAlign: 'center', padding: 24 }}>Bu teklifte henüz ürün yok</div>
      ) : (
        <>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr>
                {['Ürün', 'Miktar', 'Birim Fiyat', 'İndirim', 'Toplam', 'Durum'].map(h => (
                  <th key={h} style={{ padding: '8px 12px', textAlign: 'left', fontSize: 11, color: 'var(--text-dim)', fontWeight: 700, borderBottom: '1px solid var(--border)', textTransform: 'uppercase' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(quote.items || []).map(item => (
                <tr key={item.id} style={{ opacity: item.status !== 'active' ? 0.5 : 1 }}>
                  <td style={{ padding: '9px 12px', borderBottom: '1px solid var(--border)' }}>
                    <div style={{ fontWeight: item.status === 'active' ? 600 : 400 }}>
                      {item.product?.name || item.product_id}
                    </div>
                    {item.is_backorder && <Badge color="yellow">Beklemeli</Badge>}
                  </td>
                  <td style={{ padding: '9px 12px', borderBottom: '1px solid var(--border)' }}>{item.quantity}</td>
                  <td style={{ padding: '9px 12px', borderBottom: '1px solid var(--border)', fontWeight: 600 }}>
                    {Number(item.unit_price_try).toLocaleString('tr-TR')} ₺
                  </td>
                  <td style={{ padding: '9px 12px', borderBottom: '1px solid var(--border)', color: 'var(--green)' }}>
                    {item.discount_pct > 0 ? `%${item.discount_pct}` : '—'}
                  </td>
                  <td style={{ padding: '9px 12px', borderBottom: '1px solid var(--border)', fontWeight: 700 }}>
                    {(item.quantity * item.unit_price_try * (1 - item.discount_pct / 100)).toLocaleString('tr-TR')} ₺
                  </td>
                  <td style={{ padding: '9px 12px', borderBottom: '1px solid var(--border)' }}>
                    <Badge color={itemStatusColor(item.status)}>
                      {{ active: 'Aktif', replaced: 'Değiştirildi', removed: 'Silindi' }[item.status] || item.status}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 14, gap: 8, alignItems: 'center' }}>
            <span style={{ color: 'var(--text-dim)', fontSize: 13 }}>Aktif Toplam:</span>
            <span style={{ fontSize: 20, fontWeight: 800 }}>{total.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} ₺</span>
          </div>
        </>
      )}
    </div>
  );
}

export default function Quotes() {
  const [quotes, setQuotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(null);

  const load = () => {
    setLoading(true);
    getQuotes({ limit: 100 }).then(r => { setQuotes(r.data); setLoading(false); });
  };
  useEffect(load, []);

  return (
    <div>
      <PageHeader
        title="Teklifler"
        subtitle={`${quotes.length} teklif · 4 sn'de bir otomatik güncellenir`}
        action={<Btn icon={RefreshCw} variant="ghost" onClick={load}>Yenile</Btn>}
      />

      <Card style={{ padding: 0 }}>
        {loading ? <Spinner /> : (
          <Table headers={['', 'Teklif ID', 'Müşteri', 'Durum', 'Oluşturulma', 'Aktif Kalem']}>
            {quotes.map(q => {
              const activeCount = (q.items || []).filter(i => i.status === 'active').length;
              const isOpen = expanded === q.id;
              return (
                <>
                  <tr
                    key={q.id}
                    style={{ cursor: 'pointer' }}
                    onClick={() => setExpanded(isOpen ? null : q.id)}
                  >
                    <TD style={{ width: 32 }}>
                      {isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                    </TD>
                    <TD>
                      <span style={{ fontFamily: 'monospace', fontSize: 12 }}>{q.id.slice(0, 16)}…</span>
                    </TD>
                    <TD style={{ color: 'var(--text-dim)' }}>{q.customer_id?.slice(0, 12) || '—'}</TD>
                    <TD><Badge color={statusColor(q.status)}>{statusLabel(q.status)}</Badge></TD>
                    <TD style={{ color: 'var(--text-dim)', fontSize: 12 }}>
                      {new Date(q.created_at).toLocaleString('tr-TR')}
                    </TD>
                    <TD>
                      <Badge color={activeCount > 0 ? 'green' : 'gray'}>{activeCount} kalem</Badge>
                    </TD>
                  </tr>
                  {isOpen && (
                    <tr key={`${q.id}-detail`}>
                      <td colSpan={6} style={{ padding: '0 14px 14px' }}>
                        <QuoteDetail quoteId={q.id} onClose={() => setExpanded(null)} />
                      </td>
                    </tr>
                  )}
                </>
              );
            })}
          </Table>
        )}
      </Card>
    </div>
  );
}
