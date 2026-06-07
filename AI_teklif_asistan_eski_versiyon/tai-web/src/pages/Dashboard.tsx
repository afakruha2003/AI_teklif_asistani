import { useEffect, useState } from 'react'
import { productApi, knowledgeApi, quoteApi, sessionApi } from '../services/api'

export const Dashboard = () => {
  const [stats, setStats] = useState({
    productCount: 0,
    knowledgeCount: 0,
    quoteCount: 0,
    sessionCount: 0,
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadStats()
  }, [])

  const loadStats = async () => {
    try {
      setLoading(true)
      const [products, knowledge, quotes, sessions] = await Promise.all([
        productApi.list(),
        knowledgeApi.list(),
        quoteApi.list(),
        sessionApi.list(),
      ])

      setStats({
        productCount: products.length,
        knowledgeCount: knowledge.length,
        quoteCount: quotes.length,
        sessionCount: sessions.length,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load stats')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <div className="page-content"><p>Loading dashboard...</p></div>
  }

  return (
    <div className="page-content">
      <h1>Dashboard</h1>
      
      {error && <div className="error-banner">{error}</div>}

      <div className="stats-grid">
        <div className="stat-card">
          <h3>Products</h3>
          <p className="stat-number">{stats.productCount}</p>
          <p className="stat-label">Available Products</p>
        </div>

        <div className="stat-card">
          <h3>Knowledge Base</h3>
          <p className="stat-number">{stats.knowledgeCount}</p>
          <p className="stat-label">Knowledge Entries</p>
        </div>

        <div className="stat-card">
          <h3>Quotes</h3>
          <p className="stat-number">{stats.quoteCount}</p>
          <p className="stat-label">Active Quotes</p>
        </div>

        <div className="stat-card">
          <h3>Chat Sessions</h3>
          <p className="stat-number">{stats.sessionCount}</p>
          <p className="stat-label">Sessions</p>
        </div>
      </div>

      <div className="dashboard-info">
        <h2>Quick Info</h2>
        <p>
          This is the AI Quote Assistant administration panel. Use the navigation above to:
        </p>
        <ul>
          <li><strong>Manage Products</strong> — Add, edit, or delete products available for quotes</li>
          <li><strong>Manage Knowledge Base</strong> — Add policy information and FAQs</li>
          <li><strong>View Quotes</strong> — Monitor active quotes and see mutations from mobile app</li>
          <li><strong>Monitor Sessions</strong> — Review chat sessions and tool-call logs</li>
        </ul>
      </div>
    </div>
  )
}
