import { useState } from 'react'
import type { ProductCreate } from '../types'

interface ProductFormProps {
  onSubmit: (data: ProductCreate) => Promise<void>
  onCancel: () => void
  initialData?: ProductCreate
  loading?: boolean
}

export const ProductForm = ({ onSubmit, onCancel, initialData, loading }: ProductFormProps) => {
  const [formData, setFormData] = useState<ProductCreate>(
    initialData || {
      name: '',
      description: '',
      category: '',
      price_try: 0,
      stock: 0,
      sku: '',
      aliases: [],
      tags: [],
      is_active: true,
    }
  )

  const [aliasInput, setAliasInput] = useState('')
  const [tagInput, setTagInput] = useState('')

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? (e.target as HTMLInputElement).checked : type === 'number' ? parseFloat(value) : value,
    }))
  }

  const addAlias = () => {
    if (aliasInput.trim()) {
      setFormData(prev => {
        // Mevcut alias'ları güvenlice array olarak al
        const currentAliases = Array.isArray(prev.aliases) ? prev.aliases : ((prev.aliases as any)?.tr || []);
        return {
          ...prev,
          aliases: [...currentAliases, aliasInput.trim()] as any,
        }
      })
      setAliasInput('')
    }
  }

  const removeAlias = (index: number) => {
    setFormData(prev => {
      // Mevcut alias'ları güvenlice array olarak al
      const currentAliases = Array.isArray(prev.aliases) ? prev.aliases : ((prev.aliases as any)?.tr || []);
      return {
        ...prev,
        aliases: currentAliases.filter((_: string, i: number) => i !== index) as any,      }
    })
  }

  const addTag = () => {
    if (tagInput.trim()) {
      setFormData(prev => ({
        ...prev,
        tags: [...(prev.tags || []), tagInput.trim()],
      }))
      setTagInput('')
    }
  }

  const removeTag = (index: number) => {
    setFormData(prev => ({
      ...prev,
      tags: (prev.tags || []).filter((_: string, i: number) => i !== index),
    }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    const currentAliases = Array.isArray(formData.aliases) 
      ? formData.aliases 
      : ((formData.aliases as any)?.tr || []);

    const payloadToSend = {
      ...formData,
      aliases: { tr: currentAliases } as any 
    };

    
    try {
      await onSubmit(payloadToSend)
    } catch (error: any) {
      console.error("Save error:", error);
      alert("Kayıt başarısız!\n\nHata: " + (error.message || "Bilinmeyen bir hata oluştu."));
    }
  }

  return (
    <form onSubmit={handleSubmit} className="form">
      <div className="form-group">
        <label>Product ID</label>
        <input
          type="text"
          name="id"
          value={formData.id || ''}
          onChange={handleChange}
          placeholder="Leave empty for auto-generated"
          disabled={!!initialData}
        />
      </div>

      <div className="form-group">
        <label>Product Name *</label>
        <input
          placeholder='Enter product name'
          type="text"
          name="name"
          value={formData.name}
          onChange={handleChange}
          required
        />
      </div>

      <div className="form-group">
        <label>Description</label>
        <textarea
          name="description"
          value={formData.description || ''}
          onChange={handleChange}
          rows={3}
          placeholder="Optional product description"
        />
      </div>

      <div className="form-row">
        <div className="form-group">
          <label>Category *</label>
          <select title='category' name="category" value={formData.category} onChange={handleChange} required>
            <option value="">Select category</option>
            <option value="barcode_scanner">Barcode Scanner</option>
            <option value="terminal">Terminal</option>
            <option value="printer">Printer</option>
            <option value="software">Software License</option>
            <option value="service">Installation Service</option>
          </select>
        </div>

        <div className="form-group">
          <label>Price (TRY) *</label>
          <input
            placeholder='Enter price in Turkish Lira'
            type="number"
            name="price_try"
            value={formData.price_try}
            onChange={handleChange}
            step="0.01"
            min="0"
            required
          />
        </div>
      </div>

      <div className="form-row">
        <div className="form-group">
          <label>Stock</label>
          <input
            placeholder='Enter available stock quantity'
            type="number"
            name="stock"
            value={formData.stock || 0}
            onChange={handleChange}
            min="0"
          />
        </div>

        <div className="form-group">
          <label>SKU</label>
          <input
            placeholder='Stock Keeping Unit - optional'
            type="text"
            name="sku"
            value={formData.sku || ''}
            onChange={handleChange}
          />
        </div>
      </div>

      <div className="form-group">
        <label>Active</label>
        <input
          placeholder='Is the product active?'
          type="checkbox"
          name="is_active"
          checked={formData.is_active}
          onChange={handleChange}
        />
      </div>

      <div className="form-group">
        <label>Aliases</label>
        <div className="input-with-button">
          <input
            type="text"
            value={aliasInput}
            onChange={e => setAliasInput(e.target.value)}
            onKeyPress={e => e.key === 'Enter' && (e.preventDefault(), addAlias())}
            placeholder="Add alias and press Enter"
          />
          <button type="button" onClick={addAlias}>Add</button>
        </div>
        <div className="tags">
          {(Array.isArray(formData.aliases) ? formData.aliases : ((formData.aliases as any)?.tr || [])).map((alias: string, i: number) => (
            <span key={i} className="tag">
              {alias} <button type="button" onClick={() => removeAlias(i)}>×</button>
            </span>
          ))}
        </div>
      </div>

      <div className="form-group">
        <label>Tags</label>
        <div className="input-with-button">
          <input
            type="text"
            value={tagInput}
            onChange={e => setTagInput(e.target.value)}
            onKeyPress={e => e.key === 'Enter' && (e.preventDefault(), addTag())}
            placeholder="Add tag and press Enter"
          />
          <button type="button" onClick={addTag}>Add</button>
        </div>
        <div className="tags">
          {(formData.tags || []).map((tag: string, i: number) => (
            <span key={i} className="tag">
              {tag} <button type="button" onClick={() => removeTag(i)}>×</button>
            </span>
          ))}
        </div>
      </div>

      <div className="form-actions">
        <button type="submit" disabled={loading} className="btn-primary">
          {loading ? 'Saving...' : 'Save Product'}
        </button>
        <button type="button" onClick={onCancel} className="btn-secondary">
          Cancel
        </button>
      </div>
    </form>
  )
}