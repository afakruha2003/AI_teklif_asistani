import { useState } from 'react'
import type { KnowledgeEntryCreate } from '../types'

interface KnowledgeFormProps {
  onSubmit: (data: KnowledgeEntryCreate) => Promise<void>
  onCancel: () => void
  initialData?: KnowledgeEntryCreate
  loading?: boolean
}

export const KnowledgeForm = ({ onSubmit, onCancel, initialData, loading }: KnowledgeFormProps) => {
  const [formData, setFormData] = useState<KnowledgeEntryCreate>(
    initialData || {
      title: '',
      content: '',
      category: '',
      tags: [],
      is_active: true,
    }
  )

  const [tagInput, setTagInput] = useState('')

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? (e.target as HTMLInputElement).checked : value,
    }))
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
      tags: (prev.tags || []).filter((_, i) => i !== index),
    }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    await onSubmit(formData)
  }

  return (
    <form onSubmit={handleSubmit} className="form">
      <div className="form-group">
        <label>Title *</label>
        <input
          placeholder='Enter the title of the knowledge entry'
          type="text"
          name="title"
          value={formData.title}
          onChange={handleChange}
          required
        />
      </div>

      <div className="form-group">
        <label>Category *</label>
        <select title='category' name="category" value={formData.category} onChange={handleChange}  required>
          <option value="">Select category</option>
          <option value="policy">Policy</option>
          <option value="product_info">Product Info</option>
          <option value="pricing">Pricing</option>
          <option value="technical">Technical</option>
          <option value="faq">FAQ</option>
        </select>
      </div>

      <div className="form-group">
        <label>Content *</label>
        <textarea
          placeholder='Enter the content of the knowledge entry'
          name="content"
          value={formData.content}
          onChange={handleChange}
          rows={6}
          required
        />
      </div>

      <div className="form-group">
        <label>Active</label>
        <input
          placeholder='Is this knowledge entry active?'
          type="checkbox"
          name="is_active"
          checked={formData.is_active}
          onChange={handleChange}
        />
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
          {(formData.tags || []).map((tag, i) => (
            <span key={i} className="tag">
              {tag} <button type="button" onClick={() => removeTag(i)}>×</button>
            </span>
          ))}
        </div>
      </div>

      <div className="form-actions">
        <button type="submit" disabled={loading} className="btn-primary">
          {loading ? 'Saving...' : 'Save Knowledge Entry'}
        </button>
        <button type="button" onClick={onCancel} className="btn-secondary">
          Cancel
        </button>
      </div>
    </form>
  )
}
