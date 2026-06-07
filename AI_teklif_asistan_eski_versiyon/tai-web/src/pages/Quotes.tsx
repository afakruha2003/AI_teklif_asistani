import { useEffect, useState } from 'react'
import type { Quote } from '../types'
import { quoteApi, pollQuoteUpdates } from '../services/api'
import { Loading, Error } from '../components/Common'

export const Quotes = () => {
  const [quotes, setQuotes] = useState<Quote[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedQuote, setSelectedQuote] = useState<Quote | null>(null)
  const [searchTerm, setSearchTerm] = useState('')

  useEffect(() => {
    loadQuotes()
  }, [])

  const loadQuotes = async () => {
    try {
      setLoading(true)
      const data = await quoteApi.list()
      setQuotes(data)
      setError(null)
    } catch (err) {
      setError((err as any)?.message || 'Failed to load quotes')
    } finally {
      setLoading(false)
    }
  }

  const handleSelectQuote = async (quote: Quote) => {
    try {
      const fullQuote = await quoteApi.get(quote.id)
      setSelectedQuote(fullQuote)
      
      // Start polling for updates
      pollQuoteUpdates(quote.id, 2000, 150, (updatedQuote) => {
        setSelectedQuote(updatedQuote)
        // Also update in the list
        setQuotes(quotes.map(q => q.id === updatedQuote.id ? updatedQuote : q))
      }).catch(err => console.error('Polling error:', err))
    } catch (err) {
      setError((err as any)?.message || 'Failed to load quote details')
    }
  }

  const filteredQuotes = quotes.filter(q =>
    q.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (q.customer_id && q.customer_id.toLowerCase().includes(searchTerm.toLowerCase()))
  )

  if (loading) return <Loading message="Loading quotes..." />

  return (
    <div className="page-content">
      <div className="quotes-container">
        <div className="quotes-list">
          <h1>Quotes</h1>

          {error && <div className="error-banner">{error}</div>}

          <div className="search-bar">
            <input
              type="text"
              placeholder="Search by quote ID or customer..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
            />
          </div>

          <div className="quote-list-items">
            {filteredQuotes.map(quote => (
              <div
                key={quote.id}
                className={`quote-item ${selectedQuote?.id === quote.id ? 'active' : ''}`}
                onClick={() => handleSelectQuote(quote)}
              >
                <div className="quote-item-header">
                  <strong>{quote.id}</strong>
                  <span className={`badge badge-${quote.status}`}>
                    {quote.status}
                  </span>
                </div>
                <div className="quote-item-info">
                  {quote.customer_id && <p>Customer: {quote.customer_id}</p>}
                  <p>Items: {quote.items.filter(i => i.status === 'active').length}</p>
                  <p className="quote-total">₺{quote.total_try.toFixed(2)}</p>
                </div>
                <small>{new Date(quote.updated_at).toLocaleString()}</small>
              </div>
            ))}

            {filteredQuotes.length === 0 && (
              <div className="empty-state">
                <p>No quotes found</p>
              </div>
            )}
          </div>
        </div>

        <div className="quote-detail">
          {selectedQuote ? (
            <>
              <h2>Quote: {selectedQuote.id}</h2>
              <div className="detail-info">
                <p><strong>Status:</strong> {selectedQuote.status}</p>
                {selectedQuote.customer_id && <p><strong>Customer:</strong> {selectedQuote.customer_id}</p>}
                <p><strong>Created:</strong> {new Date(selectedQuote.created_at).toLocaleString()}</p>
                <p><strong>Updated:</strong> {new Date(selectedQuote.updated_at).toLocaleString()}</p>
                {selectedQuote.notes && <p><strong>Notes:</strong> {selectedQuote.notes}</p>}
              </div>

              <h3>Items ({selectedQuote.items.filter(i => i.status === 'active').length})</h3>
              <div className="table-container">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Product</th>
                      <th>Unit Price</th>
                      <th>Quantity</th>
                      <th>Discount</th>
                      <th>Status</th>
                      <th>Subtotal</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selectedQuote.items.map(item => (
                      <tr key={item.id} className={item.status === 'removed' ? 'removed' : ''}>
                        <td>
                          <strong>{item.product?.name || item.product_id}</strong>
                          {item.product?.sku && <small> ({item.product.sku})</small>}
                        </td>
                        <td className="text-right">₺{item.unit_price_try.toFixed(2)}</td>
                        <td className="text-center">{item.quantity}</td>
                        <td className="text-center">{item.discount_pct}%</td>
                        <td>
                          <span className={`badge badge-${item.status}`}>
                            {item.status}
                          </span>
                          {item.is_backorder && <span className="badge badge-warning">BO</span>}
                        </td>
                        <td className="text-right">
                          ₺{(item.quantity * item.unit_price_try * (1 - item.discount_pct / 100)).toFixed(2)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="quote-summary">
                <h3>Summary</h3>
                <p className="total">
                  <strong>Total:</strong> <span>₺{selectedQuote.total_try.toFixed(2)}</span>
                </p>
              </div>

              <p className="info-note">
                ℹ️ Updates from mobile app appear automatically below (real-time sync)
              </p>
            </>
          ) : (
            <div className="empty-state">
              <p>Select a quote to view details</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
