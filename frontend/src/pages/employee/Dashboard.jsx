import { useState, useEffect } from 'react'
import EmployeeLayout from '../../layouts/EmployeeLayout'
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

export default function EmployeeDashboard() {
  const [stats, setStats] = useState(null)
  const [tasks, setTasks] = useState([])
  const [error, setError] = useState('')
  const { user } = useAuth()

  const loadData = async () => {
    try {
      const [statsRes, tasksRes] = await Promise.all([
        api.get('/employee/statistics'),
        api.get('/employee/tasks'),
      ])
      setStats(statsRes.data)
      setTasks(tasksRes.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load data')
    }
  }

  useEffect(() => { loadData() }, [])

  const getStatusBadge = (status) => {
    const styles = {
      pending: 'bg-amber-100 text-amber-800',
      in_progress: 'bg-blue-100 text-blue-800',
      completed: 'bg-emerald-100 text-emerald-800',
      overdue: 'bg-red-100 text-red-800',
    }
    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold capitalize ${styles[status]}`}>
        {status.replace('_', ' ')}
      </span>
    )
  }

  const getPriorityBadge = (priority) => {
    const styles = {
      high: 'bg-red-100 text-red-800',
      medium: 'bg-amber-100 text-amber-800',
      low: 'bg-slate-100 text-slate-800',
    }
    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold capitalize ${styles[priority]}`}>
        {priority}
      </span>
    )
  }

  return (
    <EmployeeLayout>
      <div className="space-y-6">
        <div className="bg-gradient-to-r from-emerald-600 to-teal-600 rounded-2xl p-8 text-white shadow-lg">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-emerald-100 text-sm font-medium">Welcome back,</p>
              <h2 className="text-3xl font-bold mt-1">
                {user?.first_name} {user?.last_name} 👋
              </h2>
              <p className="mt-2 text-emerald-100/80 max-w-xl">
                Stay on top of your assigned tasks, update progress, and mark items as completed.
              </p>
            </div>
            <div className="flex-shrink-0">
              <div className="w-20 h-20 rounded-2xl bg-white/15 backdrop-blur flex items-center justify-center border border-white/20">
                <svg className="w-10 h-10" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" />
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
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-emerald-600"></div>
          </div>
        )}

        {stats && (
          <>
            <div className="mb-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
              My Tasks Overview
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              <StatCard
                label="Total Tasks"
                value={stats.total_tasks}
                color="bg-slate-50"
                textColor="text-slate-700"
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
                label="In Progress"
                value={stats.in_progress_tasks}
                color="bg-blue-50"
                textColor="text-blue-600"
                icon={<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20v-6M6 20V10M18 20V4"/></svg>}
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
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-lg font-semibold text-slate-800">Recent Tasks</h3>
                  <p className="text-sm text-slate-500">Your most recently assigned action items</p>
                </div>
              </div>

              {tasks.length === 0 ? (
                <div className="text-center py-12 border-2 border-dashed border-slate-200 rounded-lg">
                  <div className="w-12 h-12 mx-auto rounded-full bg-slate-100 flex items-center justify-center mb-3">
                    <svg className="w-6 h-6 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 11l3 3L22 4M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
                    </svg>
                  </div>
                  <p className="text-slate-500 font-medium">No tasks assigned yet</p>
                  <p className="text-sm text-slate-400 mt-1">Your manager will assign tasks from meeting action items.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {tasks.slice(0, 5).map((task) => (
                    <div key={task.id} className="p-4 border border-slate-200 rounded-lg hover:border-emerald-300 hover:bg-emerald-50/30 transition">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <h4 className="font-semibold text-slate-800">{task.title}</h4>
                            {getStatusBadge(task.status)}
                            {getPriorityBadge(task.priority)}
                          </div>
                          {task.description && (
                            <p className="text-sm text-slate-500 mt-1 line-clamp-2">{task.description}</p>
                          )}
                          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500">
                            {task.meeting_id && (
                              <span className="inline-flex items-center gap-1.5">
                                <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                                </svg>
                                Source: Meeting #{task.meeting_id}
                              </span>
                            )}
                            <span className="inline-flex items-center gap-1.5">
                              <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <rect x="3" y="4" width="18" height="18" rx="2"/>
                                <line x1="16" y1="2" x2="16" y2="6"/>
                                <line x1="8" y1="2" x2="8" y2="6"/>
                                <line x1="3" y1="10" x2="21" y2="10"/>
                              </svg>
                              Created {new Date(task.created_at).toLocaleDateString()}
                            </span>
                          </div>
                        </div>
                        {task.deadline && (
                          <div className="text-right flex-shrink-0">
                            <p className="text-xs font-semibold text-slate-400 uppercase">Deadline</p>
                            <p className="text-sm font-medium text-slate-700">{new Date(task.deadline).toLocaleDateString()}</p>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </EmployeeLayout>
  )
}
