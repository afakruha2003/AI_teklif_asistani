import { useEffect, useState } from 'react';
import { Plus, Pencil, Trash2, Search } from 'lucide-react';
import { getProducts, createProduct, updateProduct, deleteProduct } from '../api/client';
import {
  PageHeader, Btn, Table, TD, Badge, Spinner, Modal,
  Input, Select, Textarea, FormRow, Alert, Card,
} from '../components/UI';

const CATS = ['barkod_okuyucu', 'el_terminali', 'yazici', 'yazilim_lisansi', 'kurulum_hizmeti', 'aksesuar', 'diger'];

const EMPTY = {
  name: '', description: '', category: 'barkod_okuyucu',
  price_try: '', stock: '', sku: '', aliases: '', tags: '',
  is_active: true, alternative_product_id: '',
};

function stockColor(s) {
  if (s <= 0) return 'red';
  if (s < 5) return 'yellow';
  return 'green';
}

export default function Products() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [modal, setModal] = useState(null); // null | 'add' | 'edit'
  const [selected, setSelected] = useState(null);
  const [form, setForm] = useState(EMPTY);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const load = () => {
    setLoading(true);
    getProducts({ limit: 200 }).then(r => { setItems(r.data); setLoading(false); });
  };
  useEffect(load, []);

  const filtered = items.filter(p => {
    const s = search.toLowerCase().trim();
    if (!s) return true; // Arama kutusu boşsa hepsini göster
    
    const safeName = (p.name || '').toLowerCase();
    const safeCategory = (p.category || '').toLowerCase();
    const safeSku = (p.sku || '').toLowerCase();
    
    const safeAliasesArray = Array.isArray(p.aliases) ? p.aliases : (p.aliases?.tr || []);
    const safeAliasesStr = safeAliasesArray.join(' ').toLowerCase();

    return safeName.includes(s) || 
           safeCategory.includes(s) || 
           safeSku.includes(s) || 
           safeAliasesStr.includes(s);
  });

  const openAdd = () => { setForm(EMPTY); setSelected(null); setError(''); setModal('add'); };
  const openEdit = (p) => {
    const safeAliases = Array.isArray(p.aliases) ? p.aliases : (p.aliases?.tr || []);
    
    setForm({
      ...p,
      aliases: safeAliases.join(', '),
      tags: (p.tags || []).join(', '),
      alternative_product_id: p.alternative_product_id || '',
    });
    setSelected(p);
    setError('');
    setModal('edit');
  };

 const handleSave = async () => {
    setSaving(true); setError('');
    try {
      const aliasesArray = form.aliases ? form.aliases.split(',').map(s => s.trim()).filter(Boolean) : [];
      const tagsArray = form.tags ? form.tags.split(',').map(s => s.trim()).filter(Boolean) : [];

      const payload = {
        ...form,
        price_try: parseFloat(form.price_try) || 0,
        stock: parseInt(form.stock) || 0,
        aliases: { tr: aliasesArray }, // İŞTE BURASI: Backend'in beklediği sözlük (dict) formatı!
        tags: tagsArray,
        alternative_product_id: form.alternative_product_id || null,
      };

      if (modal === 'add') await createProduct(payload);
      else await updateProduct(selected.id, payload);
      
      setModal(null); 
      load();
    } catch (e) {
      const detail = e.response?.data?.detail;
      if (Array.isArray(detail)) {
        setError(detail.map(err => err.msg).join(' | '));
      } else {
        
        setError(typeof detail === 'string' ? detail : e.message || 'Kayıt sırasında bir hata oluştu');
      }
    }
    setSaving(false);
  };

  const handleDelete = async (id) => {
    if (!confirm('Ürünü silmek istediğinize emin misiniz?')) return;
    await deleteProduct(id); load();
  };

  return (
    <div>
      <PageHeader
        title="Ürünler"
        subtitle={`${items.length} ürün`}
        action={<Btn icon={Plus} onClick={openAdd}>Ürün Ekle</Btn>}
      />

      <Card style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <Search size={15} color="var(--text-dim)" />
          <input
            placeholder="Ürün adı, kategori, SKU ara..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{ flex: 1, background: 'none', border: 'none', color: 'var(--text)', fontSize: 13, outline: 'none' }}
          />
        </div>
      </Card>

      <Card style={{ padding: 0 }}>
        {loading ? <Spinner /> : (
          <Table headers={['Ürün', 'Kategori', 'Fiyat', 'Stok', 'SKU', 'Durum', '']}>
            {filtered.map(p => (
              <tr key={p.id}>
                <TD>
                  <div style={{ fontWeight: 600 }}>{p.name}</div>
                  {(() => {
                    const safeAliases = Array.isArray(p.aliases) ? p.aliases : (p.aliases?.tr || []);
                    return safeAliases.length > 0 ? (
                      <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 2 }}>
                        {safeAliases.slice(0, 3).join(' · ')}
                      </div>
                    ) : null;
                  })()}
                </TD>
                <TD><Badge color="blue">{p.category}</Badge></TD>
                <TD><span style={{ fontWeight: 700 }}>{Number(p.price_try).toLocaleString('tr-TR')} ₺</span></TD>
                <TD><Badge color={stockColor(p.stock)}>{p.stock}</Badge></TD>
                <TD style={{ color: 'var(--text-dim)', fontFamily: 'monospace', fontSize: 12 }}>{p.sku || '—'}</TD>
                <TD><Badge color={p.is_active ? 'green' : 'gray'}>{p.is_active ? 'Aktif' : 'Pasif'}</Badge></TD>
                <TD>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <Btn variant="ghost" icon={Pencil} onClick={() => openEdit(p)} style={{ padding: '5px 10px' }} />
                    <Btn variant="danger" icon={Trash2} onClick={() => handleDelete(p.id)} style={{ padding: '5px 10px' }} />
                  </div>
                </TD>
              </tr>
            ))}
          </Table>
        )}
      </Card>

      <Modal open={!!modal} onClose={() => setModal(null)} title={modal === 'add' ? 'Yeni Ürün' : 'Ürün Düzenle'} width={560}>
        {error && <Alert type="error">{error}</Alert>}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <Input label="Ürün Adı *" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
          <FormRow>
            <Select label="Kategori" value={form.category} onChange={e => setForm(f => ({ ...f, category: e.target.value }))}>
              {CATS.map(c => <option key={c} value={c}>{c}</option>)}
            </Select>
            <Input label="Fiyat (₺) *" type="number" value={form.price_try} onChange={e => setForm(f => ({ ...f, price_try: e.target.value }))} />
          </FormRow>
          <FormRow>
            <Input label="Stok" type="number" value={form.stock} onChange={e => setForm(f => ({ ...f, stock: e.target.value }))} />
            <Input label="SKU" value={form.sku} onChange={e => setForm(f => ({ ...f, sku: e.target.value }))} />
          </FormRow>
          <Textarea label="Açıklama" value={form.description || ''} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
          <Input label="Alias'lar (virgülle ayır)" placeholder="kablosuz okuyucu, zebra okuyucu" value={form.aliases} onChange={e => setForm(f => ({ ...f, aliases: e.target.value }))} />
          <Input label="Etiketler (virgülle ayır)" placeholder="kablosuz, barkod" value={form.tags} onChange={e => setForm(f => ({ ...f, tags: e.target.value }))} />
          <Input label="Alternatif Ürün ID" value={form.alternative_product_id} onChange={e => setForm(f => ({ ...f, alternative_product_id: e.target.value }))} />
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 13 }}>
            <input type="checkbox" checked={form.is_active} onChange={e => setForm(f => ({ ...f, is_active: e.target.checked }))} />
            Aktif
          </label>
          <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 4 }}>
            <Btn variant="ghost" onClick={() => setModal(null)}>İptal</Btn>
            <Btn onClick={handleSave} disabled={saving}>{saving ? 'Kaydediliyor...' : 'Kaydet'}</Btn>
          </div>
        </div>
      </Modal>
    </div>
  );
}
