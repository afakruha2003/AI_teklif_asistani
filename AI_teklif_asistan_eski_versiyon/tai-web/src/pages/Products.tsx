import { useEffect, useState } from 'react'
import type { Product, ProductCreate } from '../types'
import { productApi } from '../services/api'
import { Modal, Loading, Error, Success } from '../components/Common'
import { ProductForm } from '../components/ProductForm'

export const Products = () => {
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [showModal, setShowModal] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')

  useEffect(() => {
    loadProducts()
  }, [])

  const loadProducts = async () => {
    try {
      setLoading(true)
      const data = await productApi.list()
      setProducts(data)
      setError(null)
    } catch (err) {
      setError((err as any)?.message || 'Failed to load products')
    } finally {
      setLoading(false)
    }
  }

  const handleAdd = () => {
    setEditingId(null)
    setShowModal(true)
  }

  const handleEdit = (product: Product) => {
    setEditingId(product.id)
    setShowModal(true)
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this product?')) return

    try {
      await productApi.delete(id)
      setProducts(products.filter(p => p.id !== id))
      setSuccess('Product deleted successfully')
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError((err as any)?.message || 'Failed to delete product')
    }
  }

  const handleSubmit = async (data: ProductCreate) => {
    try {
      if (editingId) {
        const updated = await productApi.update(editingId, data)
        setProducts(products.map(p => (p.id === editingId ? updated : p)))
        setSuccess('Product updated successfully')
      } else {
        const created = await productApi.create(data)
        setProducts([...products, created])
        setSuccess('Product created successfully')
      }
      setShowModal(false)
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError((err as any)?.message || 'Failed to save product')
    }
  }

 const filteredProducts = products.filter(p => {
    if (!searchTerm) return true; 
    
    
    const term = searchTerm.toLowerCase().trim();
    
    const safeName = (p.name || '').toLowerCase();
    const safeCategory = (p.category || '').toLowerCase();
    
    const aliasesArray = Array.isArray(p.aliases) ? p.aliases : ((p.aliases as any)?.tr || []);
    const safeAliases = aliasesArray.join(' ').toLowerCase();

    // İster isminde, ister kategorisinde, ister eş anlamlısında geçsin, bul ve getir!
    return safeName.includes(term) || safeCategory.includes(term) || safeAliases.includes(term);
  });

  if (loading) return <Loading message="Loading products..." />

  return (
    <div className="page-content">
      <div className="page-header">
        <h1>Products</h1>
        <button onClick={handleAdd} className="btn-primary">+ Add Product</button>
      </div>

      {error && <Error message={error} onDismiss={() => setError(null)} />}
      {success && <Success message={success} onDismiss={() => setSuccess(null)} />}

      <div className="search-bar">
        <input
          type="text"
          placeholder="Search products by name or category..."
          value={searchTerm}
          onChange={e => setSearchTerm(e.target.value)}
        />
      </div>

      <div className="table-container">
        <table className="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Category</th>
              <th>Price (TRY)</th>
              <th>Stock</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredProducts.map(product => (
              <tr key={product.id}>
                <td>
                  <strong>{product.name}</strong>
                  {product.sku && <small> ({product.sku})</small>}
                </td>
                <td>{product.category}</td>
                <td className="text-right">₺{product.price_try.toFixed(2)}</td>
                <td>
                  <span className={product.stock > 0 ? 'badge-success' : 'badge-danger'}>
                    {product.stock}
                  </span>
                </td>
                <td>
                  <span className={product.is_active ? 'badge-info' : 'badge-secondary'}>
                    {product.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td>
                  <button
                    onClick={() => handleEdit(product)}
                    className="btn-small btn-info"
                    title="Edit"
                  >
                    ✎
                  </button>
                  <button
                    onClick={() => handleDelete(product.id)}
                    className="btn-small btn-danger"
                    title="Delete"
                  >
                    🗑
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {filteredProducts.length === 0 && (
          <div className="empty-state">
            <p>No products found. {searchTerm ? 'Try a different search.' : 'Create your first product!'}</p>
          </div>
        )}
      </div>

      <Modal
        isOpen={showModal}
        title={editingId ? 'Edit Product' : 'Add Product'}
        onClose={() => setShowModal(false)}
      >
        <ProductForm
          onSubmit={handleSubmit}
          onCancel={() => setShowModal(false)}
          initialData={editingId ? products.find(p => p.id === editingId) : undefined}
        />
      </Modal>
    </div>
  )
}
