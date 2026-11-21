import { useState, useEffect } from 'react'
import { NavLink } from 'react-router-dom'
import ManagerLayout from '../../layouts/ManagerLayout'
import api from '../../services/api'
import { useAuth } from '../../context/AuthContext'

const StatCard = ({ label, value, icon, color, textColor }) => (
  <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5 hover:shadow-md transition">
    <div className="flex items-start justify-between">
      <div>
        <p className="text-sm font-medium text-slate-500">{label}</p>
        <p className="mt-2 text-3xl font-bold text-slate-900">{value}</p>
      </div>
      <div className={`p-3 rounded-xl ${color}`}>
        <div className={`w-6 h-6 ${textColor}`}>{icon}</div>
      </div>
    </div>
  </div>
)

const QuickAction = ({ icon, title, desc, to }) => (
  <NavLink
    to={to}
    className="block p-5 rounded-xl border border-slate-200 bg-white hover:bg-blue-50/50 hover:border-blue-200 transition group"
  >
    <div className="w-10 h-10 rounded-lg bg-blue-50 text-blue-600 group-hover:bg-blue-100 group-hover:text-blue-700 flex items-center justify-center mb-3 transition">
      {icon}
    </div>
    <div className="font-semibold text-slate-800 group-hover:text-blue-700 transition">{title}</div>
    <div className="text-sm text-slate-500 mt-0.5">{desc}</div>
  </NavLink>
)

const PriorityBadge = ({ priority }) => {
  const styles = {
    high: 'bg-red-100 text-red-800 border-red-200',
    medium: 'bg-amber-100 text-amber-800 border-amber-200',
    low: 'bg-slate-100 text-slate-800 border-slate-200',
  }
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold capitalize border ${styles[priority] || styles.medium}`}>
      {priority || 'medium'}
    </span>
  )
}

const StatusBadge = ({ status }) => {
  const styles = {
    pending: 'bg-amber-100 text-amber-800 border-amber-200',
    in_progress: 'bg-blue-100 text-blue-800 border-blue-200',
    completed: 'bg-emerald-100 text-emerald-800 border-emerald-200',
    overdue: 'bg-red-100 text-red-800 border-red-200',
  }
  const labels = {
    pending: 'Pending',
    in_progress: 'In Progress',
    completed: 'Completed',
    overdue: 'Overdue',
  }
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold capitalize border ${styles[status] || 'bg-slate-100 text-slate-700 border-slate-200'}`}>
      {labels[status] || status?.replace('_', ' ') || status}
    </span>
  )
}

function formatDateShort(dateStr) {
  if (!dateStr) return '—'
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return dateStr
  return d.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

function formatName(u) {
  if (!u) return '—'
  const fn = u.first_name || ''
  const ln = u.last_name || ''
  const full = `${fn} ${ln}`.trim()
  if (full) return full
  return u.email || '—'
}

export default function ManagerDashboard() {
  const [stats, setStats] = useState(null)
  const [recentTasks, setRecentTasks] = useState([])
  const [error, setError] = useState('')
  const { user } = useAuth()

  const loadData = async () => {
    try {
      const [sRes, tRes] = await Promise.all([
        api.get('/manager/statistics'),
        api
          .get('/manager/tasks', { params: { sort_by: 'created_at', sort_order: 'desc', limit: 5 } })
          .then(r => r.data || [])
          .catch(() => []),
      ])
      setStats(sRes.data)
      setRecentTasks(tRes)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load statistics')
    }
  }

  useEffect(() => { loadData() }, [])

  return (
    <ManagerLayout>
      <div className="space-y-6">
        <div className="bg-gradient-to-r from-blue-600 to-cyan-600 rounded-2xl p-8 text-white shadow-lg">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-blue-100 text-sm font-medium">Welcome back,</p>
              <h2 className="text-3xl font-bold mt-1">
                {user?.first_name} {user?.last_name} 👋
              </h2>
              <p className="mt-2 text-blue-100/80 max-w-xl">
                Manage your team's meetings, track action items, and monitor commitment progress all in one place.
              </p>
            </div>
            <div className="flex-shrink-0">
              <div className="w-20 h-20 rounded-2xl bg-white/15 backdrop-blur flex items-center justify-center border border-white/20">
                <svg className="w-10 h-10" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z" />
                </svg>
              </div>
            </div>
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
            {error}
          </div>
        )}

        {!stats && !error && (
          <div className="flex items-center justify-center py-16">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600"></div>
          </div>
        )}

        {stats && (
          <>
            <div className="mb-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Overview
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              <StatCard
                label="Total Meetings"
                value={stats.total_meetings}
                color="bg-slate-50"
                textColor="text-slate-700"
                icon={<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>}
              />
              <StatCard
                label="Total Tasks"
                value={stats.total_tasks}
                color="bg-blue-50"
                textColor="text-blue-600"
                icon={<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>}
              />
              <StatCard
                label="Team Members"
                value={stats.team_members}
                color="bg-emerald-50"
                textColor="text-emerald-600"
                icon={<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>}
              />
            </div>

            <div className="mt-8 mb-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Task Status
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-5">
              <StatCard
                label="Pending"
                value={stats.pending_tasks}
                color="bg-amber-50"
                textColor="text-amber-600"
                icon={<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>}
              />
              <StatCard
                label="In Progress"
                value={stats.in_progress_tasks || 0}
                color="bg-sky-50"
                textColor="text-sky-600"
                icon={<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="9" strokeDasharray="4 3"/><path d="M12 7v5l3 2"/></svg>}
              />
              <StatCard
                label="Completed"
                value={stats.completed_tasks}
                color="bg-emerald-50"
                textColor="text-emerald-600"
                icon={<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>}
              />
              <StatCard
                label="Overdue"
                value={stats.overdue_tasks}
                color="bg-red-50"
                textColor="text-red-600"
                icon={<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>}
              />
            </div>

            <div className="mt-10 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
              <div className="flex flex-wrap items-center justify-between gap-3 px-6 py-4 border-b border-slate-200">
                <div>
                  <h3 className="text-lg font-semibold text-slate-800">Recent Tasks</h3>
                  <p className="text-sm text-slate-500 mt-0.5">Latest tasks created or linked to your meetings</p>
                </div>
                <NavLink
                  to="/manager/tasks"
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-semibold text-blue-700 rounded-lg border border-blue-200 bg-blue-50 hover:bg-blue-100 transition"
                >
                  View all tasks
                  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
                </NavLink>
              </div>
              {recentTasks.length === 0 ? (
                <div className="px-6 py-10 text-center text-sm text-slate-500">
                  No recent tasks yet. Upload a meeting and assign action items to get started.
                </div>
              ) : (
                <div className="divide-y divide-slate-100">
                  {recentTasks.map(t => (
                    <NavLink
                      key={t.id}
                      to="/manager/tasks"
                      className="block px-6 py-4 hover:bg-slate-50/80 transition"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="min-w-0 flex-1">
                          <div className="font-semibold text-slate-800 leading-snug">
                            {t.title}
                          </div>
                          {t.description && (
                            <div className="mt-1 text-sm text-slate-500 line-clamp-1">{t.description}</div>
                          )}
                          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500">
                            <span className="inline-flex items-center gap-1.5">
                              <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                              {formatName(t.assigned_user)}
                            </span>
                            <span className="inline-flex items-center gap-1.5">
                              <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
                              Due {formatDateShort(t.deadline)}
                            </span>
                          </div>
                        </div>
                        <div className="flex flex-wrap items-center justify-end gap-2 flex-shrink-0">
                          <StatusBadge status={t.status} />
                          <PriorityBadge priority={t.priority} />
                        </div>
                      </div>
                    </NavLink>
                  ))}
                </div>
              )}
            </div>

            <div className="mt-10 bg-white rounded-xl border border-slate-200 shadow-sm p-6">
              <h3 className="text-lg font-semibold text-slate-800 mb-1">Quick Actions</h3>
              <p className="text-sm text-slate-500 mb-5">Get started with your daily workflow</p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <QuickAction
                  title="Upload Meeting"
                  desc="Record or upload meeting audio"
                  to="/manager/meetings"
                  icon={<svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" /></svg>}
                />
                <QuickAction
                  title="View Tasks"
                  desc="See all action items & commitments"
                  to="/manager/tasks"
                  icon={<svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 11l3 3L22 4M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" /></svg>}
                />
                <QuickAction
                  title="View Team"
                  desc="Browse team member directory"
                  to="/manager/team"
                  icon={<svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" /></svg>}
                />
              </div>
            </div>
          </>
        )}
      </div>
    </ManagerLayout>
  )
}
