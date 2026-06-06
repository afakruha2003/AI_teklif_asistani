import { useEffect, useState } from 'react';
import { Plus, Pencil, Trash2 } from 'lucide-react';
import { getKnowledge, createKnowledge, updateKnowledge, deleteKnowledge } from '../api/client';
import {
  PageHeader, Btn, Table, TD, Badge, Spinner, Modal,
  Input, Select, Textarea, Alert, Card, FormRow,
} from '../components/UI';

const CATS = [
  'return_policy', 'delivery', 'warranty', 'pricing', 'stock',
  'compatibility', 'fallback', 'installation', 'general',
];

const CAT_LABELS = {
  return_policy: 'İade Politikası', delivery: 'Teslimat', warranty: 'Garanti',
  pricing: 'Fiyat', stock: 'Stok', compatibility: 'Uyumluluk',
  fallback: 'Fallback', installation: 'Kurulum', general: 'Genel',
};

const CAT_COLORS = {
  return_policy: 'red', delivery: 'blue', warranty: 'green',
  pricing: 'yellow', stock: 'yellow', compatibility: 'blue',
  fallback: 'gray', installation: 'green', general: 'gray',
};

const EMPTY = { title: '', content: '', category: 'general', tags: '', is_active: true };

export default function Knowledge() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(null);
  const [selected, setSelected] = useState(null);
  const [form, setForm] = useState(EMPTY);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [expanded, setExpanded] = useState(null);

  const load = () => {
    setLoading(true);
    getKnowledge({ limit: 200 }).then(r => { setItems(r.data); setLoading(false); });
  };
  useEffect(load, []);

  const openAdd = () => { setForm(EMPTY); setSelected(null); setError(''); setModal('add'); };
  const openEdit = (k) => {
    setForm({ ...k, tags: (k.tags || []).join(', ') });
    setSelected(k); setError(''); setModal('edit');
  };

  const handleSave = async () => {
    setSaving(true); setError('');
    try {
      const payload = {
        ...form,
        tags: form.tags ? form.tags.split(',').map(s => s.trim()).filter(Boolean) : [],
      };
      if (modal === 'add') await createKnowledge(payload);
      else await updateKnowledge(selected.id, payload);
      setModal(null); load();
    } catch (e) {
      setError(e.response?.data?.detail || 'Hata oluştu');
    }
    setSaving(false);
  };

  const handleDelete = async (id) => {
    if (!confirm('Bilgi kaydını silmek istiyor musunuz?')) return;
    await deleteKnowledge(id); load();
  };

  return (
    <div>
      <PageHeader
        title="Bilgi Kayıtları"
        subtitle={`${items.length} kayıt`}
        action={<Btn icon={Plus} onClick={openAdd}>Kayıt Ekle</Btn>}
      />

      <Card style={{ padding: 0 }}>
        {loading ? <Spinner /> : (
          <Table headers={['Başlık', 'Kategori', 'Etiketler', 'Durum', '']}>
            {items.map(k => (
              <>
                <tr key={k.id} style={{ cursor: 'pointer' }} onClick={() => setExpanded(expanded === k.id ? null : k.id)}>
                  <TD>
                    <div style={{ fontWeight: 600 }}>{k.title}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-dim)', fontFamily: 'monospace' }}>{k.id.slice(0, 8)}…</div>
                  </TD>
                  <TD><Badge color={CAT_COLORS[k.category] || 'gray'}>{CAT_LABELS[k.category] || k.category}</Badge></TD>
                  <TD>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                      {(k.tags || []).map(t => <Badge key={t} color="gray">{t}</Badge>)}
                    </div>
                  </TD>
                  <TD><Badge color={k.is_active ? 'green' : 'gray'}>{k.is_active ? 'Aktif' : 'Pasif'}</Badge></TD>
                  <TD>
                    <div style={{ display: 'flex', gap: 6 }} onClick={e => e.stopPropagation()}>
                      <Btn variant="ghost" icon={Pencil} onClick={() => openEdit(k)} style={{ padding: '5px 10px' }} />
                      <Btn variant="danger" icon={Trash2} onClick={() => handleDelete(k.id)} style={{ padding: '5px 10px' }} />
                    </div>
                  </TD>
                </tr>
                {expanded === k.id && (
                  <tr key={`${k.id}-exp`}>
                    <td colSpan={5} style={{ padding: '0 14px 14px', background: 'var(--surface2)' }}>
                      <div style={{ fontSize: 13, color: 'var(--text-dim)', lineHeight: 1.7, paddingTop: 10 }}>
                        {k.content}
                      </div>
                    </td>
                  </tr>
                )}
              </>
            ))}
          </Table>
        )}
      </Card>

      <Modal open={!!modal} onClose={() => setModal(null)} title={modal === 'add' ? 'Yeni Bilgi Kaydı' : 'Kayıt Düzenle'} width={540}>
        {error && <Alert type="error">{error}</Alert>}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <Input label="Başlık *" value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} />
          <FormRow cols={2}>
            <Select label="Kategori" value={form.category} onChange={e => setForm(f => ({ ...f, category: e.target.value }))}>
              {CATS.map(c => <option key={c} value={c}>{CAT_LABELS[c] || c}</option>)}
            </Select>
            <Input label="Etiketler (virgülle ayır)" value={form.tags} onChange={e => setForm(f => ({ ...f, tags: e.target.value }))} />
          </FormRow>
          <Textarea
            label="İçerik *"
            value={form.content}
            onChange={e => setForm(f => ({ ...f, content: e.target.value }))}
            style={{ minHeight: 120 }}
          />
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 13 }}>
            <input type="checkbox" checked={form.is_active} onChange={e => setForm(f => ({ ...f, is_active: e.target.checked }))} />
            Aktif
          </label>
          <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
            <Btn variant="ghost" onClick={() => setModal(null)}>İptal</Btn>
            <Btn onClick={handleSave} disabled={saving}>{saving ? 'Kaydediliyor...' : 'Kaydet'}</Btn>
          </div>
        </div>
      </Modal>
    </div>
  );
}
