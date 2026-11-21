import { useState, useEffect, useMemo } from 'react'
import ManagerLayout from '../../layouts/ManagerLayout'
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

function formatName(u) {
  if (!u) return '—'
  const fn = u.first_name || ''
  const ln = u.last_name || ''
  const full = `${fn} ${ln}`.trim()
  if (full) return full
  return u.email || '—'
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

export default function ManagerTasks() {
  const [tasks, setTasks] = useState([])
  const [allEmployees, setAllEmployees] = useState([])
  const [allMeetings, setAllMeetings] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [statusFilter, setStatusFilter] = useState('')
  const [assigneeFilter, setAssigneeFilter] = useState('')
  const [meetingFilter, setMeetingFilter] = useState('')
  const [priorityFilter, setPriorityFilter] = useState('')
  const [search, setSearch] = useState('')
  const [deadlineFrom, setDeadlineFrom] = useState('')
  const [deadlineTo, setDeadlineTo] = useState('')
  const [sortBy, setSortBy] = useState('created_at')
  const [sortOrder, setSortOrder] = useState('desc')
  const [pageSize, setPageSize] = useState('')
  const [page, setPage] = useState(1)
  const totalPages = pageSize ? Math.max(1, Math.ceil((tasks.meta?.total_count || 0) / Number(pageSize))) : 1

  const [editTask, setEditTask] = useState(null)
  const [editForm, setEditForm] = useState({ title: '', description: '', priority: 'medium', deadline: '', assigned_to: '', status: 'pending' })
  const [editError, setEditError] = useState('')
  const [editSaving, setEditSaving] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(null)
  const [deleteWorking, setDeleteWorking] = useState(false)

  const buildParams = () => {
    const p = {}
    if (statusFilter) p.status = statusFilter
    if (assigneeFilter) p.assigned_to = Number(assigneeFilter)
    if (meetingFilter) p.meeting_id = Number(meetingFilter)
    if (priorityFilter) p.priority = priorityFilter
    if (search.trim()) p.search = search.trim()
    if (deadlineFrom) p.deadline_from = deadlineFrom
    if (deadlineTo) p.deadline_to = deadlineTo
    p.sort_by = sortBy
    p.sort_order = sortOrder
    const ps = Number(pageSize)
    if (ps) {
      p.limit = ps
      p.skip = Math.max(0, (page - 1) * ps)
    }
    return p
  }

  const loadAll = async () => {
    setLoading(true)
    setError('')
    try {
      const params = buildParams()
      const [tRes, eRes, mRes] = await Promise.all([
        api.get('/manager/tasks', { params }),
        api.get('/manager/employees').catch(() => ({ data: [] })),
        api.get('/meetings').catch(() => ({ data: [] })),
      ])
      const list = Array.isArray(tRes.data) ? tRes.data : []
      setTasks({ data: list, meta: { total_count: list.length } })
      setAllEmployees(eRes.data || [])
      setAllMeetings(mRes.data || [])
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load tasks')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    setPage(1)
  }, [statusFilter, assigneeFilter, meetingFilter, priorityFilter, search, deadlineFrom, deadlineTo, sortBy, sortOrder, pageSize])

  useEffect(() => { loadAll() }, [statusFilter, assigneeFilter, meetingFilter, priorityFilter, search, deadlineFrom, deadlineTo, sortBy, sortOrder, pageSize, page])

  const list = tasks.data || []
  const meta = tasks.meta || {}

  const meetingTitleById = useMemo(() => {
    const m = new Map()
    allMeetings.forEach(mt => m.set(mt.id, mt.title))
    return m
  }, [allMeetings])

  const clearFilters = () => {
    setStatusFilter('')
    setAssigneeFilter('')
    setMeetingFilter('')
    setPriorityFilter('')
    setSearch('')
    setDeadlineFrom('')
    setDeadlineTo('')
    setSortBy('created_at')
    setSortOrder('desc')
    setPageSize('')
    setPage(1)
  }

  const openEdit = (t) => {
    setEditTask(t)
    setEditError('')
    setEditForm({
      title: t.title || '',
      description: t.description || '',
      priority: t.priority || 'medium',
      deadline: t.deadline || '',
      assigned_to: t.assigned_to ? String(t.assigned_to) : '',
      status: t.status || 'pending',
    })
  }

  const saveEdit = async (e) => {
    if (e) e.preventDefault()
    if (!editTask) return
    setEditSaving(true)
    setEditError('')
    try {
      const payload = {}
      if ((editForm.title || '') !== (editTask.title || '')) {
        payload.title = editForm.title.trim()
      }
      if ((editForm.description || '') !== (editTask.description || '')) {
        payload.description = editForm.description
      }
      if ((editForm.priority || 'medium') !== (editTask.priority || 'medium')) {
        payload.priority = editForm.priority
      }
      if ((editForm.deadline || '') !== (editTask.deadline || '')) {
        payload.deadline = editForm.deadline || null
      }
      const formAssigned = editForm.assigned_to ? Number(editForm.assigned_to) : null
      if (formAssigned && formAssigned !== editTask.assigned_to) {
        payload.assigned_to = formAssigned
      }
      if ((editForm.status || 'pending') !== (editTask.status || 'pending')) {
        payload.status = editForm.status
      }
      if (!payload.title && 'title' in payload) {
        throw new Error('Task title is required.')
      }
      if (Object.keys(payload).length === 0) {
        setEditTask(null)
        return
      }
      await api.patch(`/manager/tasks/${editTask.id}`, payload)
      setEditTask(null)
      loadAll()
    } catch (err) {
      setEditError(err.response?.data?.detail || err.message || 'Failed to save changes')
    } finally {
      setEditSaving(false)
    }
  }

  const doDelete = async () => {
    if (!confirmDelete) return
    setDeleteWorking(true)
    try {
      await api.delete(`/manager/tasks/${confirmDelete.id}`)
      setConfirmDelete(null)
      loadAll()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete task')
    } finally {
      setDeleteWorking(false)
    }
  }

  return (
    <ManagerLayout>
      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold text-slate-900">Tasks &amp; Commitments</h2>
            <p className="mt-1 text-sm text-slate-500">
              Track tasks created from meetings and assigned to your team.
            </p>
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-xl text-sm flex items-start gap-3">
            <svg className="w-5 h-5 flex-shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
            <div className="flex-1">
              <div>{error}</div>
              <button
                onClick={loadAll}
                className="mt-2 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-white border border-red-200 text-red-700 hover:bg-red-50 transition"
              >
                Retry
              </button>
            </div>
          </div>
        )}

        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-200">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="font-semibold text-slate-800">All Tasks</h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  {loading
                    ? 'Loading tasks...'
                    : `${list.length} task${list.length === 1 ? '' : 's'} shown${meta.total_count != null && meta.total_count !== list.length ? ` of ${meta.total_count}` : ''}`}
                </p>
              </div>
            </div>
            <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6 gap-3">
              <div className="lg:col-span-2 xl:col-span-2">
                <label className="block text-xs font-medium text-slate-600 mb-1">Search</label>
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search by title or description…"
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Status</label>
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  {STATUS_OPTIONS.map(o => (<option key={o.value} value={o.value}>{o.label}</option>))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Priority</label>
                <select
                  value={priorityFilter}
                  onChange={(e) => setPriorityFilter(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  {PRIORITY_OPTIONS.map(o => (<option key={o.value} value={o.value}>{o.label}</option>))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Assignee</label>
                <select
                  value={assigneeFilter}
                  onChange={(e) => setAssigneeFilter(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="">All Assignees</option>
                  {allEmployees.map(e => (<option key={e.id} value={e.id}>{formatName(e)} ({e.email})</option>))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Meeting</label>
                <select
                  value={meetingFilter}
                  onChange={(e) => setMeetingFilter(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="">All Meetings</option>
                  {allMeetings.map(m => (<option key={m.id} value={m.id}>{m.title}</option>))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Deadline From</label>
                <input
                  type="date"
                  value={deadlineFrom}
                  onChange={(e) => setDeadlineFrom(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Deadline To</label>
                <input
                  type="date"
                  value={deadlineTo}
                  onChange={(e) => setDeadlineTo(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Sort By</label>
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  {SORT_OPTIONS.map(o => (<option key={o.value} value={o.value}>{o.label}</option>))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Order</label>
                <select
                  value={sortOrder}
                  onChange={(e) => setSortOrder(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="desc">Descending</option>
                  <option value="asc">Ascending</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Per Page</label>
                <select
                  value={pageSize}
                  onChange={(e) => setPageSize(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="">All</option>
                  {PAGE_SIZE_OPTIONS.map(n => (<option key={n} value={n}>{n}</option>))}
                </select>
              </div>
              <div className="flex items-end">
                <button
                  onClick={clearFilters}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm font-medium text-slate-700 hover:bg-slate-50 transition"
                >
                  Clear Filters
                </button>
              </div>
            </div>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-20">
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600"></div>
            </div>
          ) : list.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 px-6 text-center">
              <div className="w-20 h-20 rounded-2xl bg-slate-100 flex items-center justify-center mb-4">
                <svg className="w-10 h-10 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 11l3 3L22 4M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
                </svg>
              </div>
              <h4 className="text-lg font-semibold text-slate-900">
                No tasks match these filters
              </h4>
              <p className="mt-1 text-sm text-slate-500 max-w-md">
                Try removing some filters to see more results.
              </p>
            </div>
          ) : (
            <>
              <div className="divide-y divide-slate-100">
                {list.map(t => (
                  <div key={t.id} className={`px-6 py-4 hover:bg-slate-50/60 transition ${urgencyClass(t)}`}>
                    <div className="flex flex-wrap items-start gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="font-semibold text-slate-900 leading-snug flex flex-wrap items-center gap-2">
                          <span>{t.title}</span>
                          <span className="inline-flex items-center gap-1.5 text-[11px] text-slate-400 font-normal">#{t.id}</span>
                        </div>
                        {t.description && (
                          <div className="mt-1 text-sm text-slate-600 line-clamp-2">
                            {t.description}
                          </div>
                        )}
                        <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-slate-500">
                          <div className="inline-flex items-center gap-1.5">
                            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                            <span className="text-slate-700 font-medium">{formatName(t.assigned_user)}</span>
                          </div>
                          <div className="inline-flex items-center gap-1.5">
                            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
                            <span>Due {formatDateShort(t.deadline)}</span>
                          </div>
                          {t.meeting_id && (
                            <div className="inline-flex items-center gap-1.5">
                              <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                              <span className="max-w-xs truncate text-slate-700">
                                {meetingTitleById.get(t.meeting_id) || `Meeting #${t.meeting_id}`}
                              </span>
                            </div>
                          )}
                          {t.status === 'completed' && t.completed_at && (
                            <div className="inline-flex items-center gap-1.5 text-emerald-700">
                              <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12"/></svg>
                              <span>Completed {formatDateTimeShort(t.completed_at)}</span>
                            </div>
                          )}
                        </div>
                      </div>
                      <div className="flex flex-col items-end gap-3 flex-shrink-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <StatusBadge status={t.status} />
                          <PriorityBadge priority={t.priority} />
                        </div>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => openEdit(t)}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border border-slate-300 text-slate-700 bg-white hover:bg-slate-50 transition"
                          >
                            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 1 1 3 3L7 19l-4 1 1-4 12.5-12.5z"/></svg>
                            Edit
                          </button>
                          <button
                            onClick={() => setConfirmDelete(t)}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border border-red-200 text-red-700 bg-white hover:bg-red-50 transition"
                          >
                            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2"/></svg>
                            Delete
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              {pageSize && Number(pageSize) > 0 && (
                <div className="px-6 py-3 border-t border-slate-200 flex items-center justify-between text-sm text-slate-600">
                  <div>
                    Page {page} of {totalPages}
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setPage(p => Math.max(1, p - 1))}
                      disabled={page <= 1}
                      className="px-3 py-1.5 rounded-lg border border-slate-300 text-xs font-semibold disabled:opacity-40 hover:bg-slate-50 transition"
                    >
                      Previous
                    </button>
                    <button
                      onClick={() => setPage(p => p + 1)}
                      disabled={page >= totalPages}
                      className="px-3 py-1.5 rounded-lg border border-slate-300 text-xs font-semibold disabled:opacity-40 hover:bg-slate-50 transition"
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {editTask && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm">
          <div className="w-full max-w-xl bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200 flex items-start justify-between gap-4">
              <div>
                <h3 className="font-semibold text-slate-800">Edit Task #{editTask.id}</h3>
                <p className="mt-0.5 text-xs text-slate-500">Update task details, reassign, or change status.</p>
              </div>
              <button onClick={() => setEditTask(null)} className="text-slate-400 hover:text-slate-600">
                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
              </button>
            </div>
            <form onSubmit={saveEdit} className="p-6 space-y-4">
              {editError && (
                <div className="rounded-lg bg-red-50 border border-red-200 text-red-800 text-sm px-3 py-2">{editError}</div>
              )}
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Title *</label>
                <input
                  required
                  value={editForm.title}
                  onChange={(e) => setEditForm(f => ({ ...f, title: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Description</label>
                <textarea
                  rows={3}
                  value={editForm.description}
                  onChange={(e) => setEditForm(f => ({ ...f, description: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Priority</label>
                  <select
                    value={editForm.priority}
                    onChange={(e) => setEditForm(f => ({ ...f, priority: e.target.value }))}
                    className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    {PRIORITY_EDIT_OPTIONS.map(o => (<option key={o.value} value={o.value}>{o.label}</option>))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Status</label>
                  <select
                    value={editForm.status}
                    onChange={(e) => setEditForm(f => ({ ...f, status: e.target.value }))}
                    className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    {STATUS_EDIT_OPTIONS.map(o => (<option key={o.value} value={o.value}>{o.label}</option>))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Deadline</label>
                  <input
                    type="date"
                    value={editForm.deadline}
                    onChange={(e) => setEditForm(f => ({ ...f, deadline: e.target.value }))}
                    className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Assigned To</label>
                  <select
                    value={editForm.assigned_to}
                    onChange={(e) => setEditForm(f => ({ ...f, assigned_to: e.target.value }))}
                    className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="">— select employee —</option>
                    {allEmployees.map(e => (<option key={e.id} value={e.id}>{formatName(e)} ({e.email})</option>))}
                  </select>
                </div>
              </div>
              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setEditTask(null)}
                  className="px-4 py-2 rounded-lg border border-slate-300 text-sm font-medium text-slate-700 hover:bg-slate-50 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={editSaving}
                  className="px-4 py-2 rounded-lg text-sm font-semibold bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition"
                >
                  {editSaving ? 'Saving…' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {confirmDelete && (
        <div className="fixed inset-0 z-[80] flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm">
          <div className="w-full max-w-md bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden">
            <div className="p-6">
              <div className="flex items-start gap-3">
                <div className="w-11 h-11 rounded-xl bg-red-100 text-red-700 flex items-center justify-center flex-shrink-0">
                  <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                </div>
                <div>
                  <h3 className="font-semibold text-slate-800">Delete task?</h3>
                  <p className="mt-1 text-sm text-slate-600">
                    Are you sure you want to delete <span className="font-medium text-slate-800">“{confirmDelete.title}”</span>?
                    This cannot be undone.
                  </p>
                </div>
              </div>
            </div>
            <div className="px-6 py-4 border-t border-slate-200 flex items-center justify-end gap-2 bg-slate-50/60">
              <button
                onClick={() => setConfirmDelete(null)}
                disabled={deleteWorking}
                className="px-4 py-2 rounded-lg border border-slate-300 text-sm font-medium text-slate-700 hover:bg-white disabled:opacity-50 transition"
              >
                Cancel
              </button>
              <button
                onClick={doDelete}
                disabled={deleteWorking}
                className="px-4 py-2 rounded-lg text-sm font-semibold bg-red-600 text-white hover:bg-red-700 disabled:opacity-50 transition"
              >
                {deleteWorking ? 'Deleting…' : 'Delete Task'}
              </button>
            </div>
          </div>
        </div>
      )}
    </ManagerLayout>
  )
}
