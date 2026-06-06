import { useEffect, useState } from 'react';
import { MessageSquare, Wrench, ChevronDown, ChevronRight, CheckCircle, XCircle } from 'lucide-react';
import { getSessions, getSessionMessages, getSessionToolCalls } from '../api/client';
import { PageHeader, Table, TD, Badge, Spinner, Card, Btn } from '../components/UI';

function RoleChip({ role }) {
  const colors = { user: 'blue', assistant: 'green', tool: 'yellow' };
  const labels = { user: 'Kullanıcı', assistant: 'Asistan', tool: 'Tool' };
  return <Badge color={colors[role] || 'gray'}>{labels[role] || role}</Badge>;
}

function SessionDetail({ sessionId }) {
  const [tab, setTab] = useState('messages');
  const [messages, setMessages] = useState([]);
  const [toolCalls, setToolCalls] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      getSessionMessages(sessionId),
      getSessionToolCalls(sessionId),
    ]).then(([m, t]) => {
      setMessages(m.data);
      setToolCalls(t.data);
      setLoading(false);
    });
  }, [sessionId]);

  if (loading) return <Spinner />;

  return (
    <div style={{ marginTop: 12, background: 'var(--surface2)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
      {/* Tabs */}
      <div style={{ display: 'flex', borderBottom: '1px solid var(--border)' }}>
        {[
          { id: 'messages', icon: MessageSquare, label: `Mesajlar (${messages.length})` },
          { id: 'toolcalls', icon: Wrench, label: `Tool Calls (${toolCalls.length})` },
        ].map(({ id, icon: Icon, label }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            style={{
              display: 'flex', alignItems: 'center', gap: 7,
              padding: '10px 18px', border: 'none', cursor: 'pointer', fontSize: 13,
              background: tab === id ? 'var(--accent-dim)' : 'transparent',
              color: tab === id ? 'var(--accent)' : 'var(--text-dim)',
              fontWeight: tab === id ? 600 : 400,
              borderBottom: tab === id ? '2px solid var(--accent)' : '2px solid transparent',
            }}
          >
            <Icon size={13} />{label}
          </button>
        ))}
      </div>

      {tab === 'messages' && (
        <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 10, maxHeight: 420, overflowY: 'auto' }}>
          {messages.length === 0 && <div style={{ color: 'var(--text-dim)', textAlign: 'center', padding: 20 }}>Mesaj yok</div>}
          {messages.map(msg => (
            <div key={msg.id} style={{
              display: 'flex', gap: 10, alignItems: 'flex-start',
              flexDirection: msg.role === 'user' ? 'row-reverse' : 'row',
            }}>
              <div style={{ flexShrink: 0, marginTop: 2 }}>
                <RoleChip role={msg.role} />
              </div>
              <div style={{
                maxWidth: '75%', padding: '10px 14px', borderRadius: 10, fontSize: 13, lineHeight: 1.6,
                background: msg.role === 'user' ? 'var(--accent-dim)' : 'var(--surface)',
                border: '1px solid var(--border)',
              }}>
                {msg.content}
                <div style={{ fontSize: 10, color: 'var(--text-dim)', marginTop: 4 }}>
                  {new Date(msg.created_at).toLocaleTimeString('tr-TR')}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {tab === 'toolcalls' && (
        <div style={{ maxHeight: 480, overflowY: 'auto' }}>
          {toolCalls.length === 0 && <div style={{ color: 'var(--text-dim)', textAlign: 'center', padding: 20 }}>Tool call yok</div>}
          {toolCalls.map(tc => (
            <div key={tc.id} style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                {tc.status === 'success'
                  ? <CheckCircle size={14} color="var(--green)" />
                  : <XCircle size={14} color="var(--red)" />
                }
                <span style={{ fontWeight: 700, fontFamily: 'monospace', fontSize: 13 }}>{tc.tool_name}</span>
                <Badge color="gray">seq: {tc.sequence_num}</Badge>
                {tc.duration_ms && <Badge color="gray">{tc.duration_ms}ms</Badge>}
                {tc.idempotency_key && <Badge color="blue">idempotent</Badge>}
              </div>

              {tc.input_data && (
                <div style={{ marginBottom: 6 }}>
                  <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 3 }}>INPUT</div>
                  <pre style={{ fontSize: 11, background: 'var(--surface)', padding: '8px 10px', borderRadius: 6, overflow: 'auto', color: 'var(--text-dim)', margin: 0 }}>
                    {JSON.stringify(tc.input_data, null, 2)}
                  </pre>
                </div>
              )}

              {tc.quote_delta && (
                <div style={{ marginTop: 6 }}>
                  <div style={{ fontSize: 11, color: 'var(--accent)', marginBottom: 3 }}>QUOTE DELTA</div>
                  <pre style={{ fontSize: 11, background: 'var(--accent-dim)', padding: '8px 10px', borderRadius: 6, overflow: 'auto', color: 'var(--accent)', margin: 0 }}>
                    {JSON.stringify(tc.quote_delta, null, 2)}
                  </pre>
                </div>
              )}

              {tc.output_data?.error && (
                <div style={{ marginTop: 6, fontSize: 12, color: 'var(--red)', padding: '6px 10px', background: '#450a0a', borderRadius: 6 }}>
                  ⚠ {tc.output_data.error}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function Sessions() {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(null);

  useEffect(() => {
    getSessions({ limit: 50 }).then(r => { setSessions(r.data); setLoading(false); });
  }, []);

  return (
    <div>
      <PageHeader
        title="Oturumlar & Tool Call Logları"
        subtitle="Mobil sohbet oturumları ve tüm tool-call geçmişi"
      />

      <Card style={{ padding: 0 }}>
        {loading ? <Spinner /> : (
          <Table headers={['', 'Oturum ID', 'Teklif ID', 'Müşteri', 'Başlangıç']}>
            {sessions.length === 0 && (
              <tr><td colSpan={5} style={{ padding: 32, textAlign: 'center', color: 'var(--text-dim)' }}>Henüz oturum yok</td></tr>
            )}
            {sessions.map(s => {
              const isOpen = expanded === s.id;
              return (
                <>
                  <tr key={s.id} style={{ cursor: 'pointer' }} onClick={() => setExpanded(isOpen ? null : s.id)}>
                    <TD style={{ width: 32 }}>{isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}</TD>
                    <TD><span style={{ fontFamily: 'monospace', fontSize: 12 }}>{s.id.slice(0, 18)}…</span></TD>
                    <TD style={{ fontFamily: 'monospace', fontSize: 12, color: 'var(--text-dim)' }}>
                      {s.quote_id ? s.quote_id.slice(0, 14) + '…' : '—'}
                    </TD>
                    <TD style={{ color: 'var(--text-dim)' }}>{s.customer_id?.slice(0, 12) || '—'}</TD>
                    <TD style={{ fontSize: 12, color: 'var(--text-dim)' }}>
                      {new Date(s.created_at).toLocaleString('tr-TR')}
                    </TD>
                  </tr>
                  {isOpen && (
                    <tr key={`${s.id}-detail`}>
                      <td colSpan={5} style={{ padding: '0 14px 14px' }}>
                        <SessionDetail sessionId={s.id} />
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
