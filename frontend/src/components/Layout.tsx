import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import {
  Activity,
  BrainCircuit,
  Building2,
  ChevronDown,
  FileText,
  FlaskConical,
  LayoutDashboard,
  LogOut,
  Menu,
  Microscope,
  Settings,
  Target,
  X,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { cn } from './ui'

interface NavItem {
  to: string
  label: string
  icon: typeof Activity
  roles?: string[]
}

const groups: { title: string; items: NavItem[] }[] = [
  {
    title: 'Monitor',
    items: [
      { to: '/app', label: 'Overview', icon: LayoutDashboard },
      { to: '/app/monitor', label: 'Live Monitor', icon: Activity },
    ],
  },
  {
    title: 'Understand',
    items: [
      { to: '/app/analysis', label: 'AI Analysis', icon: BrainCircuit },
      { to: '/app/baseline', label: 'My Baseline', icon: Target },
      { to: '/app/lab', label: 'BioSignal Lab', icon: FlaskConical },
    ],
  },
  {
    title: 'Research',
    items: [
      { to: '/app/research', label: 'Research Centre', icon: Microscope },
      { to: '/app/institution', label: 'Institution Insights', icon: Building2, roles: ['researcher', 'admin'] },
    ],
  },
  {
    title: 'Records',
    items: [
      { to: '/app/reports', label: 'Reports & History', icon: FileText },
      { to: '/app/settings', label: 'Settings', icon: Settings },
    ],
  },
]

function Brand({ dark = true }: { dark?: boolean }) {
  return (
    <div className="flex items-center gap-2.5">
      <span className="flex h-9 w-9 items-center justify-center rounded-[11px] bg-[#DFE8D7]">
        <svg viewBox="0 0 32 32" className="h-6 w-6" fill="none" aria-hidden>
          <path
            d="M4 18c2.2 0 2.2-7 4.4-7s2.2 12 4.4 12 2.2-9 4.4-9 2.2 5 4.4 5 2.2-2 4.4-2"
            stroke="#183D32"
            strokeWidth="1.7"
            strokeLinecap="round"
          />
          <circle cx="25" cy="10" r="2" fill="#D49A45" />
        </svg>
      </span>
      <div>
        <p className={cn('font-display text-[17px] leading-none', dark ? 'text-[#F4F3E9]' : 'text-forest')}>AuraSense</p>
        <p className={cn('mt-1 text-[9px] uppercase tracking-[0.22em]', dark ? 'text-[#91A58E]' : 'text-muted')}>
          Signal research
        </p>
      </div>
    </div>
  )
}

export { Brand }

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(() => {
    setMobileOpen(false)
    setMenuOpen(false)
    window.scrollTo({ top: 0 })
  }, [location.pathname])

  const visibleGroups = groups
    .map((group) => ({
      ...group,
      items: group.items.filter((item) => !item.roles || (user && item.roles.includes(user.role))),
    }))
    .filter((group) => group.items.length > 0)

  const current = groups.flatMap((g) => g.items).find((item) =>
    item.to === '/app' ? location.pathname === '/app' : location.pathname.startsWith(item.to),
  )

  const initials = (user?.name || 'AS')
    .split(' ')
    .map((part) => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()

  const navBody = (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between px-5 pb-6 pt-6">
        <Brand />
        <button className="text-[#91A58E] lg:hidden" onClick={() => setMobileOpen(false)} aria-label="Close navigation">
          <X size={18} />
        </button>
      </div>
      <nav className="scroll-thin flex-1 overflow-y-auto px-3 pb-4">
        {visibleGroups.map((group) => (
          <div key={group.title} className="mb-5">
            <p className="mb-2 px-3 text-[9px] font-semibold uppercase tracking-[0.2em] text-[#6E8479]">{group.title}</p>
            <div className="space-y-0.5">
              {group.items.map((item) => {
                const Icon = item.icon
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.to === '/app'}
                    className={({ isActive }) =>
                      cn(
                        'group flex items-center gap-2.5 rounded-lg px-3 py-2 text-[12.5px] transition-colors',
                        isActive
                          ? 'bg-[#F4F3E9] font-medium text-forest'
                          : 'text-[#C3D0C4] hover:bg-[#1B3B31] hover:text-[#F4F3E9]',
                      )
                    }
                  >
                    <Icon size={15} className="shrink-0 opacity-80" />
                    <span className="truncate">{item.label}</span>
                  </NavLink>
                )
              })}
            </div>
          </div>
        ))}
      </nav>
      <div className="border-t border-[#26463B] px-5 py-4">
        <p className="text-[10px] leading-relaxed text-[#8FA396]">
          Research prototype. Estimates describe physiological pattern similarity — not a diagnosis.
        </p>
        <div className="mt-3 flex items-center gap-1.5 text-[9px] uppercase tracking-[0.14em] text-[#6E8479]">
          <span className="breathe h-1.5 w-1.5 rounded-full bg-[#91A58E]" />
          Model online
        </div>
      </div>
    </div>
  )

  return (
    <div className="min-h-screen bg-ivory">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-[242px] bg-forest-deep lg:block">{navBody}</aside>

      {mobileOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-[#102A23]/50" onClick={() => setMobileOpen(false)} />
          <aside className="absolute inset-y-0 left-0 w-[264px] bg-forest-deep">{navBody}</aside>
        </div>
      )}

      <div className="lg:pl-[242px]">
        <header className="sticky top-0 z-20 border-b border-line bg-ivory/90 backdrop-blur">
          <div className="flex h-14 items-center justify-between gap-3 px-4 md:px-7">
            <div className="flex min-w-0 items-center gap-3">
              <button className="text-forest lg:hidden" onClick={() => setMobileOpen(true)} aria-label="Open navigation">
                <Menu size={19} />
              </button>
              <div className="min-w-0">
                <p className="truncate text-[13px] font-medium text-forest">{current?.label || 'AuraSense'}</p>
                <p className="hidden truncate text-[10px] text-muted sm:block">
                  {user?.role === 'individual' ? 'Personal workspace' : user?.role === 'researcher' ? 'Research workspace' : 'Institution workspace'}
                  {user?.is_demo ? ' · demonstration data' : ''}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <span className="hidden items-center gap-1.5 rounded-full border border-line bg-paper px-2.5 py-1 text-[10px] text-muted md:inline-flex">
                <span className="breathe h-1.5 w-1.5 rounded-full bg-sage" />
                WESAD model
              </span>
              <div className="relative">
                <button
                  onClick={() => setMenuOpen((value) => !value)}
                  className="flex items-center gap-2 rounded-full border border-line bg-paper py-1 pl-1 pr-2.5 transition hover:border-sage"
                  aria-expanded={menuOpen}
                >
                  <span className="flex h-6 w-6 items-center justify-center rounded-full bg-forest text-[9px] font-semibold text-[#F4F3E9]">
                    {initials}
                  </span>
                  <span className="hidden max-w-[120px] truncate text-[11px] text-charcoal sm:block">{user?.name}</span>
                  <ChevronDown size={12} className="text-muted" />
                </button>
                {menuOpen && (
                  <>
                    <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
                    <div className="absolute right-0 z-20 mt-2 w-56 rounded-xl border border-line bg-paper p-1.5 shadow-lg">
                      <div className="px-2.5 py-2">
                        <p className="truncate text-[12px] font-medium text-charcoal">{user?.name}</p>
                        <p className="truncate text-[10px] text-muted">{user?.email}</p>
                        <p className="mt-1.5 inline-flex rounded-full bg-[#EEF1E7] px-2 py-0.5 text-[9px] uppercase tracking-[0.1em] text-[#5E6E4C]">
                          {user?.role}
                        </p>
                      </div>
                      <div className="hairline my-1" />
                      <button
                        onClick={() => navigate('/app/settings')}
                        className="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-[12px] text-charcoal hover:bg-[#F4F3EB]"
                      >
                        <Settings size={14} /> Account settings
                      </button>
                      <button
                        onClick={() => {
                          logout()
                          navigate('/')
                        }}
                        className="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-[12px] text-[#A45545] hover:bg-[#FAEDE9]"
                      >
                        <LogOut size={14} /> Sign out
                      </button>
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>
        </header>

        <main className="mx-auto w-full max-w-[1320px] px-4 pb-16 pt-6 md:px-7 md:pt-8">
          <Outlet />
          <footer className="mt-12 flex flex-col gap-2 border-t border-line pt-5 text-[10px] leading-relaxed text-muted md:flex-row md:items-center md:justify-between">
            <p>AuraSense · Research prototype · Not a medical device and not clinically validated.</p>
            <p className="mono">WESAD · GroupKFold participant-independent evaluation</p>
          </footer>
        </main>
      </div>
    </div>
  )
}
