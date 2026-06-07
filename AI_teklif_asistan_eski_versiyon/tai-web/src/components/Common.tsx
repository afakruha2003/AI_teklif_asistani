import React, { type ReactNode } from 'react'

interface ModalProps {
  isOpen: boolean
  title: string
  children: ReactNode
  onClose: () => void
}

export const Modal = ({ isOpen, title, children, onClose }: ModalProps) => {
  if (!isOpen) return null

  return (
    <>
      <div className="modal-overlay" onClick={onClose}></div>
      <div className="modal">
        <div className="modal-header">
          <h2>{title}</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        <div className="modal-body">
          {children}
        </div>
      </div>
    </>
  )
}

interface NavProps {
  currentPage: string
  onNavigate: (page: string) => void
}

export const Navigation = ({ currentPage, onNavigate }: NavProps) => {
  const pages = [
    { id: 'dashboard', label: 'Dashboard' },
    { id: 'products', label: 'Products' },
    { id: 'knowledge', label: 'Knowledge' },
    { id: 'quotes', label: 'Quotes' },
    { id: 'sessions', label: 'Sessions' },
  ]

  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <h1>TAI — Quote Assistant</h1>
      </div>
      <div className="navbar-menu">
        {pages.map(page => (
          <button
            key={page.id}
            className={`nav-link ${currentPage === page.id ? 'active' : ''}`}
            onClick={() => onNavigate(page.id)}
          >
            {page.label}
          </button>
        ))}
      </div>
    </nav>
  )
}

interface LoadingProps {
  message?: string
}

export const Loading = ({ message = 'Loading...' }: LoadingProps) => (
  <div className="loading">
    <div className="spinner"></div>
    <p>{message}</p>
  </div>
)

interface ErrorProps {
  message: string
  onDismiss?: () => void
}

export const Error = ({ message, onDismiss }: ErrorProps) => (
  <div className="error-banner">
    <span>{message}</span>
    {onDismiss && <button onClick={onDismiss}>×</button>}
  </div>
)

interface SuccessProps {
  message: string
  onDismiss?: () => void
}

export const Success = ({ message, onDismiss }: SuccessProps) => (
  <div className="success-banner">
    <span>{message}</span>
    {onDismiss && <button onClick={onDismiss}>×</button>}
  </div>
)
