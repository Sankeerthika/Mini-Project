import { useState, useEffect } from 'react'
import AdminLayout from '../../layouts/AdminLayout'
import api from '../../services/api'

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

export default function AdminDashboard() {
  const [stats, setStats] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get('/admin/statistics')
      .then((res) => setStats(res.data))
      .catch((err) => setError(err.response?.data?.detail || 'Failed to load statistics'))
  }, [])

  return (
    <AdminLayout>
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Dashboard Overview</h2>
          <p className="mt-1 text-sm text-slate-500">Platform-wide statistics at a glance</p>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
            {error}
          </div>
        )}

        {!stats && !error && (
          <div className="flex items-center justify-center py-16">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-600"></div>
          </div>
        )}

        {stats && (
          <>
            <div className="mb-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Users
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
              <StatCard
                label="Total Users"
                value={stats.total_users}
                color="bg-indigo-50"
                textColor="text-indigo-600"
                icon={<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>}
              />
              <StatCard
                label="Admins"
                value={stats.total_admins}
                color="bg-purple-50"
                textColor="text-purple-600"
                icon={<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>}
              />
              <StatCard
                label="Managers"
                value={stats.total_managers}
                color="bg-blue-50"
                textColor="text-blue-600"
                icon={<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>}
              />
              <StatCard
                label="Employees"
                value={stats.total_employees}
                color="bg-green-50"
                textColor="text-green-600"
                icon={<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="19" y1="8" x2="19" y2="14"/><line x1="22" y1="11" x2="16" y2="11"/></svg>}
              />
            </div>

            <div className="mt-8 mb-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Meetings & Tasks
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-5">
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
                color="bg-indigo-50"
                textColor="text-indigo-600"
                icon={<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>}
              />
              <StatCard
                label="Pending"
                value={stats.pending_tasks}
                color="bg-amber-50"
                textColor="text-amber-600"
                icon={<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>}
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

            <div className="mt-10 bg-white rounded-xl border border-slate-200 shadow-sm p-6">
              <h3 className="text-lg font-semibold text-slate-800 mb-1">Quick Actions</h3>
              <p className="text-sm text-slate-500 mb-5">Get started managing your platform</p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <a
                  href="/admin/users"
                  className="p-5 rounded-xl border border-slate-200 hover:border-indigo-300 hover:bg-indigo-50/40 transition group"
                >
                  <div className="w-10 h-10 rounded-lg bg-indigo-100 text-indigo-600 flex items-center justify-center mb-3 group-hover:bg-indigo-600 group-hover:text-white transition">
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" /></svg>
                  </div>
                  <div className="font-semibold text-slate-900">Add User</div>
                  <div className="text-sm text-slate-500 mt-0.5">Create Admin, Manager, or Employee</div>
                </a>
                <a
                  href="/admin/users"
                  className="p-5 rounded-xl border border-slate-200 hover:border-indigo-300 hover:bg-indigo-50/40 transition group"
                >
                  <div className="w-10 h-10 rounded-lg bg-indigo-100 text-indigo-600 flex items-center justify-center mb-3 group-hover:bg-indigo-600 group-hover:text-white transition">
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
                  </div>
                  <div className="font-semibold text-slate-900">Manage Users</div>
                  <div className="text-sm text-slate-500 mt-0.5">Edit roles, deactivate accounts</div>
                </a>
                <a
                  href="/admin/profile"
                  className="p-5 rounded-xl border border-slate-200 hover:border-indigo-300 hover:bg-indigo-50/40 transition group"
                >
                  <div className="w-10 h-10 rounded-lg bg-indigo-100 text-indigo-600 flex items-center justify-center mb-3 group-hover:bg-indigo-600 group-hover:text-white transition">
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg>
                  </div>
                  <div className="font-semibold text-slate-900">View Profile</div>
                  <div className="text-sm text-slate-500 mt-0.5">See your account information</div>
                </a>
              </div>
            </div>
          </>
        )}
      </div>
    </AdminLayout>
  )
}
