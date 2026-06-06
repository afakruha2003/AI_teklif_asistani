import { useEffect, useState } from 'react'
import type { KnowledgeEntry, KnowledgeEntryCreate } from '../types'
import { knowledgeApi } from '../services/api'
import { Modal, Loading, Error, Success } from '../components/Common'
import { KnowledgeForm } from '../components/KnowledgeForm'

export const Knowledge = () => {
  const [entries, setEntries] = useState<KnowledgeEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [showModal, setShowModal] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')

  useEffect(() => {
    loadEntries()
  }, [])

  const loadEntries = async () => {
    try {
      setLoading(true)
      const data = await knowledgeApi.list()
      setEntries(data)
      setError(null)
    } catch (err) {
      setError((err as any)?.message || 'Failed to load knowledge entries')
    } finally {
      setLoading(false)
    }
  }

  const handleAdd = () => {
    setEditingId(null)
    setShowModal(true)
  }

  const handleEdit = (entry: KnowledgeEntry) => {
    setEditingId(entry.id)
    setShowModal(true)
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this entry?')) return

    try {
      await knowledgeApi.delete(id)
      setEntries(entries.filter(e => e.id !== id))
      setSuccess('Knowledge entry deleted successfully')
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError((err as any)?.message || 'Failed to delete entry')
    }
  }

  const handleSubmit = async (data: KnowledgeEntryCreate) => {
    try {
      if (editingId) {
        const updated = await knowledgeApi.update(editingId, data)
        setEntries(entries.map(e => (e.id === editingId ? updated : e)))
        setSuccess('Knowledge entry updated successfully')
      } else {
        const created = await knowledgeApi.create(data)
        setEntries([...entries, created])
        setSuccess('Knowledge entry created successfully')
      }
      setShowModal(false)
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError((err as any)?.message || 'Failed to save entry')
    }
  }

  const filteredEntries = entries.filter(e =>
    e.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    e.category.toLowerCase().includes(searchTerm.toLowerCase())
  )

  if (loading) return <Loading message="Loading knowledge base..." />

  return (
    <div className="page-content">
      <div className="page-header">
        <h1>Knowledge Base</h1>
        <button onClick={handleAdd} className="btn-primary">+ Add Entry</button>
      </div>

      {error && <Error message={error} onDismiss={() => setError(null)} />}
      {success && <Success message={success} onDismiss={() => setSuccess(null)} />}

      <div className="search-bar">
        <input
          type="text"
          placeholder="Search by title or category..."
          value={searchTerm}
          onChange={e => setSearchTerm(e.target.value)}
        />
      </div>

      <div className="entries-grid">
        {filteredEntries.map(entry => (
          <div key={entry.id} className="entry-card">
            <div className="entry-header">
              <h3>{entry.title}</h3>
              <span className="badge">{entry.category}</span>
            </div>
            <p className="entry-preview">{entry.content.substring(0, 100)}...</p>
            <div className="entry-tags">
              {entry.tags.map(tag => (
                <span key={tag} className="tag-small">{tag}</span>
              ))}
            </div>
            <div className="entry-footer">
              <small>{entry.is_active ? '✓ Active' : '✗ Inactive'}</small>
              <div className="entry-actions">
                <button
                  onClick={() => handleEdit(entry)}
                  className="btn-small btn-info"
                  title="Edit"
                >
                  ✎
                </button>
                <button
                  onClick={() => handleDelete(entry.id)}
                  className="btn-small btn-danger"
                  title="Delete"
                >
                  🗑
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {filteredEntries.length === 0 && (
        <div className="empty-state">
          <p>No knowledge entries found. {searchTerm ? 'Try a different search.' : 'Create your first entry!'}</p>
        </div>
      )}

      <Modal
        isOpen={showModal}
        title={editingId ? 'Edit Knowledge Entry' : 'Add Knowledge Entry'}
        onClose={() => setShowModal(false)}
      >
        <KnowledgeForm
          onSubmit={handleSubmit}
          onCancel={() => setShowModal(false)}
          initialData={editingId ? entries.find(e => e.id === editingId) : undefined}
        />
      </Modal>
    </div>
  )
}
