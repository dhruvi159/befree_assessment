import React from 'react'
import {
  LayoutDashboard,
  Upload,
  ArrowLeftRight,
  Sparkles,
  BarChart3,
  Settings,
  PanelLeftClose,
  PanelLeftOpen,
  X,
} from 'lucide-react'
import type { Page } from '../../types'

interface SidebarProps {
  page: Page
  setPage: (p: Page) => void
  collapsed: boolean
  setCollapsed: (c: boolean) => void
  mobileOpen: boolean
  setMobileOpen: (o: boolean) => void
  flaggedCount?: number
}

const navItems: Array<{ id: Page; label: string; icon: React.ReactNode }> = [
  { id: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard size={18} /> },
  { id: 'upload', label: 'Upload Statement', icon: <Upload size={18} /> },
  { id: 'transactions', label: 'Transactions', icon: <ArrowLeftRight size={18} /> },
  { id: 'classification', label: 'Classification', icon: <Sparkles size={18} /> },
  { id: 'reports', label: 'Reports & Analytics', icon: <BarChart3 size={18} /> },
  { id: 'settings', label: 'Settings', icon: <Settings size={18} /> },
]

export function Sidebar({
  page,
  setPage,
  collapsed,
  setCollapsed,
  mobileOpen,
  setMobileOpen,
  flaggedCount = 0,
}: SidebarProps) {
  return (
    <aside className={`sidebar ${collapsed ? 'collapsed' : ''} ${mobileOpen ? 'mobile-open' : ''}`}>
      <div className="brand">
        <div className="brand-mark">
          <span />
          <span />
          <span />
        </div>
        {!collapsed && <span>StatementIQ</span>}
        <button className="mobile-close" onClick={() => setMobileOpen(false)}>
          <X size={18} />
        </button>
      </div>

      <nav>
        {navItems.map((item) => (
          <button
            key={item.id}
            className={page === item.id ? 'active' : ''}
            onClick={() => {
              setPage(item.id)
              setMobileOpen(false)
            }}
          >
            {item.icon}
            <span>{item.label}</span>
            {item.id === 'transactions' && flaggedCount > 0 && !collapsed && (
              <b>{flaggedCount}</b>
            )}
          </button>
        ))}
      </nav>

      <div className="sidebar-bottom">
        <button className="collapse-btn" onClick={() => setCollapsed(!collapsed)}>
          {collapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
          <span>{collapsed ? 'Expand' : 'Collapse'}</span>
        </button>
      </div>
    </aside>
  )
}

