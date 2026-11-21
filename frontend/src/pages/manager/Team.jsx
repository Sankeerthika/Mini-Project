import { useState, useEffect } from 'react'
import ManagerLayout from '../../layouts/ManagerLayout'
import api from '../../services/api'

function formatName(u) {
  const fn = u.first_name || ''
  const ln = u.last_name || ''
  const full = `${fn} ${ln}`.trim()
  if (full) return full
  return u.email
}

function getInitials(u) {
  const fn = (u.first_name || '').trim().charAt(0).toUpperCase()
  const ln = (u.last_name || '').trim().charAt(0).toUpperCase()
  if (fn || ln) return fn + ln
  return (u.email || '?').charAt(0).toUpperCase()
}

export default function ManagerTeam() {
  const [employees, setEmployees] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadEmployees = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await api.get('/manager/employees')
      setEmployees(res.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load team members')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadEmployees() }, [])

  return (
    <ManagerLayout>
      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold text-slate-900">Team</h2>
            <p className="mt-1 text-sm text-slate-500">
              Active employees you can assign tasks to.
            </p>
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-xl text-sm flex items-start gap-3">
            <svg className="w-5 h-5 flex-shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
            <div className="flex-1">
              <div>{error}</div>
              <button
                onClick={loadEmployees}
                className="mt-2 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-white border border-red-200 text-red-700 hover:bg-red-50 transition"
              >
                Retry
              </button>
            </div>
          </div>
        )}

        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="font-semibold text-slate-800">Active Team Members</h3>
              <p className="text-xs text-slate-500 mt-0.5">
                {loading
                  ? 'Loading team members...'
                  : `${employees.length} employee${employees.length === 1 ? '' : 's'}`}
              </p>
            </div>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-20">
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600"></div>
            </div>
          ) : employees.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 px-6 text-center">
              <div className="w-20 h-20 rounded-2xl bg-slate-100 flex items-center justify-center mb-4">
                <svg className="w-10 h-10 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </div>
              <h4 className="text-lg font-semibold text-slate-900">No team members yet</h4>
              <p className="mt-1 text-sm text-slate-500 max-w-md">
                There are no active employees in the system yet. An administrator can add employee accounts from the Admin panel.
              </p>
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {employees.map((emp) => (
                <div key={emp.id} className="px-6 py-4 flex items-center gap-4 hover:bg-slate-50/60 transition">
                  <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-emerald-500 to-teal-600 text-white flex items-center justify-center font-bold text-lg flex-shrink-0">
                    {getInitials(emp)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold text-slate-900">{formatName(emp)}</div>
                    <div className="text-sm text-slate-500 flex items-center gap-1.5 mt-0.5">
                      <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
                      <span className="truncate">{emp.email}</span>
                    </div>
                  </div>
                  <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                    Active
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </ManagerLayout>
  )
}
