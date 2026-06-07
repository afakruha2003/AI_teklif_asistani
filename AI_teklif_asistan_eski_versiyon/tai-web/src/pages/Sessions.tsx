import { useEffect, useState } from 'react'
import type { ChatSession, ChatMessage, ToolCallLog } from '../types'
import { sessionApi } from '../services/api'
import { Loading, Error } from '../components/Common'

export const Sessions = () => {
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [selectedSession, setSelectedSession] = useState<ChatSession | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [toolCalls, setToolCalls] = useState<ToolCallLog[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'messages' | 'tools'>('messages')
  const [searchTerm, setSearchTerm] = useState('')

  useEffect(() => {
    loadSessions()
  }, [])

  const loadSessions = async () => {
    try {
      setLoading(true)
      const data = await sessionApi.list()
      setSessions(data.sort((a, b) => 
        new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      ))
      setError(null)
    } catch (err) {
      setError((err as any)?.message || 'Failed to load sessions')
    } finally {
      setLoading(false)
    }
  }

  const handleSelectSession = async (session: ChatSession) => {
    try {
      setSelectedSession(session)
      const [sessionMessages, sessionToolCalls] = await Promise.all([
        sessionApi.getMessages(session.id),
        sessionApi.getToolCalls(session.id),
      ])
      setMessages(sessionMessages)
      setToolCalls(sessionToolCalls.sort((a, b) => a.sequence_num - b.sequence_num))
    } catch (err) {
      setError((err as any)?.message || 'Failed to load session details')
    }
  }

  const filteredSessions = sessions.filter(s =>
    s.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (s.quote_id && s.quote_id.toLowerCase().includes(searchTerm.toLowerCase())) ||
    (s.customer_id && s.customer_id.toLowerCase().includes(searchTerm.toLowerCase()))
  )

  if (loading) return <Loading message="Loading sessions..." />

  return (
    <div className="page-content">
      <div className="sessions-container">
        <div className="sessions-list">
          <h1>Chat Sessions</h1>

          {error && <Error message={error} onDismiss={() => setError(null)} />}

          <div className="search-bar">
            <input
              type="text"
              placeholder="Search by session, quote, or customer..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
            />
          </div>

          <div className="session-list-items">
            {filteredSessions.map(session => (
              <div
                key={session.id}
                className={`session-item ${selectedSession?.id === session.id ? 'active' : ''}`}
                onClick={() => handleSelectSession(session)}
              >
                <div className="session-item-header">
                  <strong>{session.id.substring(0, 12)}...</strong>
                </div>
                <div className="session-item-info">
                  {session.quote_id && <p>Quote: {session.quote_id}</p>}
                  {session.customer_id && <p>Customer: {session.customer_id}</p>}
                </div>
                <small>{new Date(session.updated_at).toLocaleString()}</small>
              </div>
            ))}

            {filteredSessions.length === 0 && (
              <div className="empty-state">
                <p>No sessions found</p>
              </div>
            )}
          </div>
        </div>

        <div className="session-detail">
          {selectedSession ? (
            <>
              <h2>Session: {selectedSession.id}</h2>
              <div className="detail-info">
                {selectedSession.quote_id && <p><strong>Quote:</strong> {selectedSession.quote_id}</p>}
                {selectedSession.customer_id && <p><strong>Customer:</strong> {selectedSession.customer_id}</p>}
                <p><strong>Created:</strong> {new Date(selectedSession.created_at).toLocaleString()}</p>
                <p><strong>Updated:</strong> {new Date(selectedSession.updated_at).toLocaleString()}</p>
              </div>

              <div className="tabs">
                <button
                  className={`tab ${activeTab === 'messages' ? 'active' : ''}`}
                  onClick={() => setActiveTab('messages')}
                >
                  Messages ({messages.length})
                </button>
                <button
                  className={`tab ${activeTab === 'tools' ? 'active' : ''}`}
                  onClick={() => setActiveTab('tools')}
                >
                  Tool Calls ({toolCalls.length})
                </button>
              </div>

              {activeTab === 'messages' && (
                <div className="messages-list">
                  {messages.length === 0 ? (
                    <p className="empty-state-text">No messages</p>
                  ) : (
                    messages.map(msg => (
                      <div key={msg.id} className={`message ${msg.role}`}>
                        <div className="message-header">
                          <strong>{msg.role.toUpperCase()}</strong>
                          <small>{new Date(msg.created_at).toLocaleTimeString()}</small>
                        </div>
                        <div className="message-content">{msg.content}</div>
                      </div>
                    ))
                  )}
                </div>
              )}

              {activeTab === 'tools' && (
                <div className="tools-list">
                  {toolCalls.length === 0 ? (
                    <p className="empty-state-text">No tool calls</p>
                  ) : (
                    toolCalls.map(call => (
                      <div key={call.id} className="tool-call">
                        <div className="tool-header">
                          <strong>#{call.sequence_num} - {call.tool_name}</strong>
                          <span className={`badge badge-${call.status}`}>{call.status}</span>
                          {call.duration_ms && <small>{call.duration_ms}ms</small>}
                        </div>
                        
                        {call.input_data && (
                          <details className="tool-details">
                            <summary>Input</summary>
                            <pre>{JSON.stringify(call.input_data, null, 2)}</pre>
                          </details>
                        )}

                        {call.output_data && (
                          <details className="tool-details">
                            <summary>Output</summary>
                            <pre>{JSON.stringify(call.output_data, null, 2)}</pre>
                          </details>
                        )}

                        {call.quote_delta && (
                          <details className="tool-details">
                            <summary>Quote Delta</summary>
                            <pre>{JSON.stringify(call.quote_delta, null, 2)}</pre>
                          </details>
                        )}

                        <small className="text-muted">
                          {new Date(call.created_at).toLocaleString()}
                          {call.idempotency_key && ` | Key: ${call.idempotency_key}`}
                        </small>
                      </div>
                    ))
                  )}
                </div>
              )}
            </>
          ) : (
            <div className="empty-state">
              <p>Select a session to view details</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
