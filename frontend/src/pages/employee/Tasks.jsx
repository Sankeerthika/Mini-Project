import { useState, useEffect, useMemo } from 'react'
import EmployeeLayout from '../../layouts/EmployeeLayout'
import api from '../../services/api'

const PriorityBadge = ({ priority }) => {
  const styles = {
    high: 'bg-red-100 text-red-800 border-red-200',
    medium: 'bg-amber-100 text-amber-800 border-amber-200',
    low: 'bg-slate-100 text-slate-800 border-slate-200',
  }
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold capitalize border ${styles[priority] || styles.medium}`}>
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
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold capitalize border ${styles[status] || 'bg-slate-100 text-slate-700 border-slate-200'}`}>
      {labels[status] || String(status || 'pending').replace('_', ' ')}
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

function formatDateTimeShort(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return ''
  return d.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function urgencyClass(task) {
  if (!task || task.status === 'completed') return ''
  if (!task.deadline) return ''
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const d = new Date(task.deadline)
  d.setHours(0, 0, 0, 0)
  const days = Math.round((d - today) / (1000 * 60 * 60 * 24))
  if (days < 0) return 'bg-red-50/70 border-l-4 border-l-red-500'
  if (days === 0) return 'bg-amber-50/70 border-l-4 border-l-amber-500'
  if (days <= 3) return 'bg-sky-50/60 border-l-4 border-l-sky-400'
  return ''
}

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'pending', label: 'Pending' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'completed', label: 'Completed' },
  { value: 'overdue', label: 'Overdue' },
]

const PRIORITY_OPTIONS = [
  { value: '', label: 'All Priorities' },
  { value: 'high', label: 'High' },
  { value: 'medium', label: 'Medium' },
  { value: 'low', label: 'Low' },
]

const SORT_OPTIONS = [
  { value: 'created_at', label: 'Created At' },
  { value: 'deadline', label: 'Deadline' },
  { value: 'priority', label: 'Priority' },
  { value: 'status', label: 'Status' },
  { value: 'title', label: 'Title' },
]

const PAGE_SIZE_OPTIONS = [10, 25, 50]

const STATUS_EDIT_OPTIONS = STATUS_OPTIONS.filter(o => o.value !== '')
const PRIORITY_EDIT_OPTIONS = PRIORITY_OPTIONS.filter(o => o.value !== '')

export default function EmployeeTasks() {
  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [successMsg, setSuccessMsg] = useState('')

  const [statusFilter, setStatusFilter] = useState('')
  const [priorityFilter, setPriorityFilter] = useState('')
  const [search, setSearch] = useState('')
  const [deadlineFrom, setDeadlineFrom] = useState('')
  const [deadlineTo, setDeadlineTo] = useState('')
  const [sortBy, setSortBy] = useState('created_at')
  const [sortOrder, setSortOrder] = useState('desc')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState('')

  const [editingTask, setEditingTask] = useState(null)
  const [editBaseline, setEditBaseline] = useState(null)
  const [editLoading, setEditLoading] = useState(false)
  const [editError, setEditError] = useState('')

  const loadTasks = async () => {
    setLoading(true)
    setError('')
    try {
      const params = {}
      if (statusFilter) params.status = statusFilter
      if (priorityFilter) params.priority = priorityFilter
      if (search.trim()) params.search = search.trim()
      if (deadlineFrom) params.deadline_from = deadlineFrom
      if (deadlineTo) params.deadline_to = deadlineTo
      if (sortBy) params.sort_by = sortBy
      if (sortOrder) params.sort_order = sortOrder
      if (pageSize) {
        params.limit = Number(pageSize)
        params.skip = (page - 1) * Number(pageSize)
      }
      const res = await api.get('/employee/tasks', { params })
      setTasks(res.data || [])
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load tasks')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadTasks() }, [statusFilter, priorityFilter, deadlineFrom, deadlineTo, sortBy, sortOrder, page, pageSize])

  useEffect(() => {
    const t = setTimeout(() => { loadTasks() }, 450)
    return () => clearTimeout(t)
  }, [search])

  useEffect(() => {
    if (successMsg) {
      const t = setTimeout(() => setSuccessMsg(''), 4000)
      return () => clearTimeout(t)
    }
  }, [successMsg])

  useEffect(() => { setPage(1) }, [statusFilter, priorityFilter, search, deadlineFrom, deadlineTo, sortBy, sortOrder, pageSize])

  const clearFilters = () => {
    setStatusFilter('')
    setPriorityFilter('')
    setSearch('')
    setDeadlineFrom('')
    setDeadlineTo('')
    setSortBy('created_at')
    setSortOrder('desc')
    setPage(1)
    setPageSize('')
  }

  const openEdit = (task) => {
    setEditingTask({
      title: task.title || '',
      description: task.description || '',
      priority: task.priority || 'medium',
      deadline: task.deadline ? new Date(task.deadline).toISOString().split('T')[0] : '',
      status: task.status || 'pending',
    })
    setEditBaseline({
      title: task.title || '',
      description: task.description || '',
      priority: task.priority || 'medium',
      deadline: task.deadline ? new Date(task.deadline).toISOString().split('T')[0] : '',
      status: task.status || 'pending',
      id: task.id,
    })
    setEditError('')
  }

  const closeEdit = () => {
    if (editLoading) return
    setEditingTask(null)
    setEditBaseline(null)
    setEditError('')
  }

  const saveEdit = async () => {
    if (editLoading || !editBaseline) return
    if (!editingTask.title.trim()) {
      setEditError('Title cannot be empty.')
      return
    }
    const ALLOWED = ['title', 'description', 'priority', 'deadline', 'status']
    const payload = {}
    for (const key of ALLOWED) {
      const base = editBaseline[key]
      const cur = editingTask[key]
      if (cur !== base) {
        if (key === 'deadline') payload[key] = cur || null
        else if (key === 'description') payload[key] = cur === '' ? null : cur
        else payload[key] = cur
      }
    }
    if (Object.keys(payload).length === 0) {
      closeEdit()
      return
    }
    setEditLoading(true)
    setEditError('')
    try {
      await api.patch(`/employee/tasks/${editBaseline.id}`, payload)
      setSuccessMsg('Task updated.')
      closeEdit()
      await loadTasks()
    } catch (err) {
      const detail = err.response?.data?.detail
      setEditError(typeof detail === 'string' ? detail : 'Failed to update task.')
    } finally {
      setEditLoading(false)
    }
  }

  const updateTaskStatus = async (taskId, newStatus) => {
    try {
      await api.patch(`/employee/tasks/${taskId}`, { status: newStatus })
      setSuccessMsg('Status updated.')
      await loadTasks()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update task')
    }
  }

  const hasPagination = !!pageSize
  const canPrev = hasPagination && page > 1
  const canNext = hasPagination && tasks.length >= Number(pageSize)

  return (
    <EmployeeLayout>
      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold text-slate-900">My Tasks</h2>
            <p className="mt-1 text-sm text-slate-500">View and update your assigned action items</p>
          </div>
        </div>

        {successMsg && (
          <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 px-4 py-3 rounded-xl text-sm flex items-start gap-2.5">
            <svg className="w-5 h-5 flex-shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="20 6 9 17 4 12" />
            </svg>
            <div className="font-semibold">{successMsg}</div>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl text-sm">
            {error}
          </div>
        )}

        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Search</label>
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search title or description…"
                className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Status</label>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500 bg-white"
              >
                {STATUS_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Priority</label>
              <select
                value={priorityFilter}
                onChange={(e) => setPriorityFilter(e.target.value)}
                className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500 bg-white"
              >
                {PRIORITY_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Deadline From</label>
              <input
                type="date"
                value={deadlineFrom}
                onChange={(e) => setDeadlineFrom(e.target.value)}
                className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Deadline To</label>
              <input
                type="date"
                value={deadlineTo}
                onChange={(e) => setDeadlineTo(e.target.value)}
                className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Sort By</label>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500 bg-white"
              >
                {SORT_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Sort Order</label>
              <select
                value={sortOrder}
                onChange={(e) => setSortOrder(e.target.value)}
                className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500 bg-white"
              >
                <option value="desc">Descending</option>
                <option value="asc">Ascending</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Page Size</label>
              <select
                value={pageSize}
                onChange={(e) => setPageSize(e.target.value)}
                className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500 bg-white"
              >
                <option value="">All</option>
                {PAGE_SIZE_OPTIONS.map(n => <option key={n} value={String(n)}>{n} per page</option>)}
              </select>
            </div>
          </div>
          <div className="mt-4 flex items-center justify-end gap-2">
            <button
              onClick={clearFilters}
              className="px-4 py-2 rounded-lg border border-slate-300 text-sm font-semibold text-slate-700 hover:bg-slate-50 transition"
            >
              Clear
            </button>
            <button
              onClick={loadTasks}
              className="px-4 py-2 rounded-lg bg-emerald-600 text-sm font-semibold text-white hover:bg-emerald-700 transition shadow-sm"
            >
              Refresh
            </button>
          </div>
        </div>

        {loading && (
          <div className="flex items-center justify-center py-16">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-emerald-600"></div>
          </div>
        )}

        {!loading && tasks.length === 0 && (
          <div className="text-center py-16 border-2 border-dashed border-slate-200 rounded-xl bg-white">
            <div className="w-16 h-16 mx-auto rounded-full bg-slate-100 flex items-center justify-center mb-4">
              <svg className="w-8 h-8 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 11l3 3L22 4M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
              </svg>
            </div>
            <p className="text-slate-700 font-semibold text-lg">No tasks found</p>
            <p className="text-sm text-slate-400 mt-1">Try adjusting the filters or check back later.</p>
          </div>
        )}

        {!loading && tasks.length > 0 && (
          <>
            <div className="space-y-4">
              {tasks.map((task) => (
                <div key={task.id} className={`bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden ${urgencyClass(task)}`}>
                  <div className="p-5">
                    <div className="flex flex-wrap items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <h3 className="text-lg font-semibold text-slate-900">{task.title}</h3>
                          <StatusBadge status={task.status} />
                          <PriorityBadge priority={task.priority} />
                        </div>
                        {task.description && (
                          <p className="mt-2 text-slate-600 whitespace-pre-wrap">{task.description}</p>
                        )}
                        <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-1.5 text-xs text-slate-500">
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
                            Created {formatDateTimeShort(task.created_at)}
                          </span>
                          {task.status === 'completed' && task.completed_at && (
                            <span className="inline-flex items-center gap-1.5 text-emerald-700 font-medium">
                              <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <polyline points="20 6 9 17 4 12"/>
                              </svg>
                              Completed {formatDateTimeShort(task.completed_at)}
                            </span>
                          )}
                        </div>
                      </div>
                      {task.deadline && (
                        <div className="text-right">
                          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Deadline</p>
                          <p className="text-base font-semibold text-slate-800">{formatDateShort(task.deadline)}</p>
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="px-5 py-3 bg-slate-50 border-t border-slate-200">
                    <div className="flex flex-wrap items-center gap-3">
                      <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Quick Status:</span>
                      {STATUS_EDIT_OPTIONS.map((opt) => (
                        <button
                          key={opt.value}
                          onClick={() => updateTaskStatus(task.id, opt.value)}
                          disabled={task.status === opt.value}
                          className={`px-3 py-1.5 rounded-lg text-xs font-semibold text-white transition disabled:opacity-50 disabled:cursor-not-allowed ${
                            opt.value === 'pending' ? 'bg-amber-500 hover:bg-amber-600'
                            : opt.value === 'in_progress' ? 'bg-blue-500 hover:bg-blue-600'
                            : opt.value === 'completed' ? 'bg-emerald-500 hover:bg-emerald-600'
                            : opt.value === 'overdue' ? 'bg-red-500 hover:bg-red-600'
                            : 'bg-slate-500 hover:bg-slate-600'
                          }`}
                        >
                          {opt.label}
                        </button>
                      ))}
                      <div className="flex-1"></div>
                      <button
                        onClick={() => openEdit(task)}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 transition"
                      >
                        <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M12 20h9"/>
                          <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
                        </svg>
                        Edit
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {hasPagination && (
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm px-4 py-3 flex flex-wrap items-center justify-between gap-3">
                <div className="text-sm text-slate-500">
                  Page <span className="font-semibold text-slate-700">{page}</span>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={!canPrev}
                    className="px-3 py-1.5 rounded-lg text-sm font-semibold border border-slate-300 text-slate-700 hover:bg-slate-50 transition disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    Previous
                  </button>
                  <span className="px-3 py-1.5 text-sm font-semibold text-slate-600">{page}</span>
                  <button
                    onClick={() => setPage(p => p + 1)}
                    disabled={!canNext}
                    className="px-3 py-1.5 rounded-lg text-sm font-semibold border border-slate-300 text-slate-700 hover:bg-slate-50 transition disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {editingTask && editBaseline && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200 flex items-start justify-between gap-4">
              <div>
                <h3 className="text-lg font-bold text-slate-900">Edit Task #{editBaseline.id}</h3>
                <p className="text-xs text-slate-500 mt-0.5">Update details of this assigned task.</p>
              </div>
              <button
                onClick={closeEdit}
                disabled={editLoading}
                className="p-2 rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition disabled:opacity-40"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            </div>
            <div className="p-6 space-y-5 max-h-[75vh] overflow-y-auto">
              {editError && (
                <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-xl text-sm">{editError}</div>
              )}
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1.5">Title <span className="text-red-500">*</span></label>
                <input
                  type="text"
                  value={editingTask.title}
                  onChange={(e) => setEditingTask({ ...editingTask, title: e.target.value })}
                  className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500"
                />
              </div>
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1.5">Description</label>
                <textarea
                  rows={4}
                  value={editingTask.description}
                  onChange={(e) => setEditingTask({ ...editingTask, description: e.target.value })}
                  className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500"
                />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1.5">Priority</label>
                  <select
                    value={editingTask.priority}
                    onChange={(e) => setEditingTask({ ...editingTask, priority: e.target.value })}
                    className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500 bg-white"
                  >
                    {PRIORITY_EDIT_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1.5">Status</label>
                  <select
                    value={editingTask.status}
                    onChange={(e) => setEditingTask({ ...editingTask, status: e.target.value })}
                    className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500 bg-white"
                  >
                    {STATUS_EDIT_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1.5">Deadline</label>
                <input
                  type="date"
                  value={editingTask.deadline}
                  onChange={(e) => setEditingTask({ ...editingTask, deadline: e.target.value })}
                  className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500"
                />
              </div>
            </div>
            <div className="px-6 py-4 border-t border-slate-200 flex items-center justify-end gap-3">
              <button
                onClick={closeEdit}
                disabled={editLoading}
                className="px-5 py-2 rounded-xl border border-slate-300 text-slate-700 font-semibold hover:bg-slate-50 transition disabled:opacity-40"
              >
                Cancel
              </button>
              <button
                onClick={saveEdit}
                disabled={editLoading}
                className="px-5 py-2 rounded-xl bg-emerald-600 text-white font-semibold hover:bg-emerald-700 transition disabled:opacity-50 shadow-sm"
              >
                {editLoading ? 'Saving…' : 'Save Changes'}
              </button>
            </div>
          </div>
        </div>
      )}
    </EmployeeLayout>
  )
}
