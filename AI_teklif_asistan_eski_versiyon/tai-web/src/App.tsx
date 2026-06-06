import { useState } from 'react'
import './App.css'
import { Navigation } from './components/Common'
import { Dashboard } from './pages/Dashboard'
import { Products } from './pages/Products'
import { Knowledge } from './pages/Knowledge'
import { Quotes } from './pages/Quotes'
import { Sessions } from './pages/Sessions'

type Page = 'dashboard' | 'products' | 'knowledge' | 'quotes' | 'sessions'

function App() {
  const [currentPage, setCurrentPage] = useState<Page>('dashboard')

  const renderPage = () => {
    switch (currentPage) {
      case 'dashboard':
        return <Dashboard />
      case 'products':
        return <Products />
      case 'knowledge':
        return <Knowledge />
      case 'quotes':
        return <Quotes />
      case 'sessions':
        return <Sessions />
      default:
        return <Dashboard />
    }
  }

  return (
    <div className="app">
      <Navigation currentPage={currentPage} onNavigate={setCurrentPage as (page: string) => void} />
      <main>{renderPage()}</main>
    </div>
  )
}

export default App
