import { useState, useEffect, useRef } from 'react'
import ManagerLayout from '../../layouts/ManagerLayout'
import api from '../../services/api'

function formatFileSize(bytes) {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

function formatDate(dateStr) {
  if (!dateStr) return '—'
  const d = new Date(dateStr)
  return d.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function StatusBadge({ status }) {
  const styles = {
    uploaded: 'bg-blue-50 text-blue-700 border-blue-200',
    processing: 'bg-amber-50 text-amber-700 border-amber-200',
    completed: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    failed: 'bg-red-50 text-red-700 border-red-200',
  }
  const labels = {
    uploaded: 'Uploaded — Awaiting Processing',
    processing: 'Processing',
    completed: 'Completed',
    failed: 'Failed',
  }
  const cls = styles[status] || 'bg-slate-50 text-slate-700 border-slate-200'
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${cls}`}>
      {status === 'uploaded' && (
        <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
      )}
      {status === 'processing' && (
        <svg className="w-3 h-3 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>
      )}
      {status === 'completed' && (
        <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="20 6 9 17 4 12"/></svg>
      )}
      {status === 'failed' && (
        <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
      )}
      {labels[status] || status}
    </span>
  )
}

const TaskStatusBadge = ({ status }) => {
  const styles = {
    pending: 'bg-amber-100 text-amber-800 border-amber-200',
    in_progress: 'bg-blue-100 text-blue-800 border-blue-200',
    completed: 'bg-emerald-100 text-emerald-800 border-emerald-200',
    overdue: 'bg-red-100 text-red-800 border-red-200',
  }
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold capitalize border ${styles[status] || 'bg-slate-100 text-slate-700 border-slate-200'}`}>
      {String(status || 'pending').replace('_', ' ')}
    </span>
  )
}

const TaskPriorityBadge = ({ priority }) => {
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

function formatName(u) {
  if (!u) return ''
  const fn = u.first_name || ''
  const ln = u.last_name || ''
  const full = `${fn} ${ln}`.trim()
  if (full) return full
  return u.email || ''
}

function getInitials(u) {
  if (!u) return '?'
  const fn = (u.first_name || '').trim().charAt(0).toUpperCase()
  const ln = (u.last_name || '').trim().charAt(0).toUpperCase()
  if (fn || ln) return fn + ln
  return (u.email || '?').charAt(0).toUpperCase()
}

function parseDeadlineToISO(raw) {
  if (!raw) return ''
  const s = String(raw).trim()
  if (!s) return ''
  const explicit = new Date(s)
  if (!isNaN(explicit.getTime())) {
    return explicit.toISOString().slice(0, 10)
  }
  const m1 = s.match(/(\d{1,2}[\/\-\.](\d{1,2})[\/\-\.](\d{2,4}))/)
  if (m1) {
    const p = new Date(s)
    if (!isNaN(p.getTime())) return p.toISOString().slice(0, 10)
  }
  return ''
}

export default function ManagerMeetings() {
  const [meetings, setMeetings] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [successMsg, setSuccessMsg] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [selectedFile, setSelectedFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadError, setUploadError] = useState('')
  const fileInputRef = useRef(null)
  const [transcribingId, setTranscribingId] = useState(null)
  const [analyzingId, setAnalyzingId] = useState(null)
  const [detailMeeting, setDetailMeeting] = useState(null)
  const [creatingTaskIndex, setCreatingTaskIndex] = useState(null)
  const [submittingTask, setSubmittingTask] = useState(false)
  const [taskDraft, setTaskDraft] = useState({
    title: '',
    description: '',
    priority: 'medium',
    deadline: '',
    assigned_to: '',
    personReference: '',
  })
  const [employees, setEmployees] = useState([])
  const [employeesLoaded, setEmployeesLoaded] = useState(false)

  const [taskError, setTaskError] = useState('')
  const [taskSuccess, setTaskSuccess] = useState('')
  const [createdTask, setCreatedTask] = useState(null)

  const [linkedTasks, setLinkedTasks] = useState([])
  const [linkedTasksLoading, setLinkedTasksLoading] = useState(false)

  const hasAnalysis = (m) => {
    if (!m) return false
    const hasSummary = !!(m.summary && m.summary.trim())
    const hasDecisions = !!(m.key_decisions && m.key_decisions.trim())
    const hasActionItems = !!(m.action_items_json && m.action_items_json.trim())
    return hasSummary && hasDecisions && hasActionItems
  }

  const parseJSON = (text, fallback) => {
    if (!text || !text.trim()) return fallback
    try {
      const v = JSON.parse(text)
      return v
    } catch (e) {
      return fallback
    }
  }

  const loadMeetings = async () => {
    try {
      setLoading(true)
      setError('')
      const res = await api.get('/meetings')
      setMeetings(res.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load meetings')
    } finally {
      setLoading(false)
    }
  }

  const loadEmployees = async () => {
    if (employeesLoaded) return true
    try {
      const res = await api.get('/manager/employees')
      setEmployees(res.data || [])
      setEmployeesLoaded(true)
      return true
    } catch (err) {
      const detail = err.response?.data?.detail
      setTaskError(typeof detail === 'string' ? detail : 'Failed to load employees')
      return false
    }
  }

  useEffect(() => {
    loadMeetings()
  }, [])

  useEffect(() => {
    if (successMsg) {
      const t = setTimeout(() => setSuccessMsg(''), 4000)
      return () => clearTimeout(t)
    }
  }, [successMsg])

  useEffect(() => {
    if (error) {
      const t = setTimeout(() => setError(''), 6000)
      return () => clearTimeout(t)
    }
  }, [error])

  useEffect(() => {
    if (taskSuccess) {
      const t = setTimeout(() => setTaskSuccess(''), 5000)
      return () => clearTimeout(t)
    }
  }, [taskSuccess])

  useEffect(() => {
    if (taskError) {
      const t = setTimeout(() => setTaskError(''), 6000)
      return () => clearTimeout(t)
    }
  }, [taskError])

  useEffect(() => {
    let cancelled = false
    if (detailMeeting && detailMeeting.id) {
      setLinkedTasksLoading(true)
      api.get('/manager/tasks', { params: { meeting_id: detailMeeting.id } })
        .then(r => { if (!cancelled) setLinkedTasks(r.data || []) })
        .catch(() => { if (!cancelled) setLinkedTasks([]) })
        .finally(() => { if (!cancelled) setLinkedTasksLoading(false) })
    } else {
      setLinkedTasks([])
    }
    return () => { cancelled = true }
  }, [detailMeeting?.id])

  const handleStartCreateTask = async (index, actionItem) => {
    if (submittingTask || creatingTaskIndex !== null) return
    setTaskError('')
    setTaskSuccess('')
    setCreatedTask(null)
    const ok = await loadEmployees()
    if (!ok) return
    setTaskDraft({
      title: actionItem?.task?.toString() || '',
      description: '',
      priority: 'medium',
      deadline: parseDeadlineToISO(actionItem?.deadline),
      assigned_to: '',
      personReference: actionItem?.person?.toString() || '',
    })
    setCreatingTaskIndex(index)
  }

  const handleCloseTaskDialog = () => {
    if (submittingTask) return
    setCreatingTaskIndex(null)
    setTaskDraft({
      title: '',
      description: '',
      priority: 'medium',
      deadline: '',
      assigned_to: '',
      personReference: '',
    })
    setTaskError('')
    setTaskSuccess('')
    setCreatedTask(null)
  }

  const handleSubmitTask = async () => {
    if (submittingTask || creatingTaskIndex === null || !detailMeeting) return
    if (!taskDraft.title.trim()) {
      setTaskError('Task title is required.')
      return
    }
    if (!taskDraft.assigned_to) {
      setTaskError('Please select an employee to assign this task to.')
      return
    }
    try {
      setSubmittingTask(true)
      setTaskError('')
      setTaskSuccess('')
      const payload = {
        title: taskDraft.title.trim(),
        description: taskDraft.description.trim() || undefined,
        priority: taskDraft.priority || 'medium',
        deadline: taskDraft.deadline || undefined,
        assigned_to: String(taskDraft.assigned_to),
        meeting_id: detailMeeting.id,
      }
      const res = await api.post('/manager/tasks', payload)
      setSubmittingTask(false)
      setCreatedTask(res.data)
      setTaskSuccess('Task created successfully.')
      setLinkedTasks(prev => Array.isArray(prev) ? [res.data, ...prev] : [res.data])
      setTimeout(() => {
        handleCloseTaskDialog()
      }, 1500)
    } catch (err) {
      setSubmittingTask(false)
      const detail = err.response?.data?.detail
      if (typeof detail === 'string') setTaskError(detail)
      else if (Array.isArray(detail)) setTaskError(detail.map((d) => d.msg || JSON.stringify(d)).join('; '))
      else setTaskError('Failed to create task. Please try again.')
    }
  }

  const resetForm = () => {
    setTitle('')
    setDescription('')
    setSelectedFile(null)
    setUploadProgress(0)
    setUploadError('')
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const openModal = () => {
    resetForm()
    setShowModal(true)
  }

  const closeModal = () => {
    if (uploading) return
    setShowModal(false)
    resetForm()
  }

  const handleFileChange = (e) => {
    const file = e.target.files?.[0]
    if (file) {
      setSelectedFile(file)
      setUploadError('')
    }
  }

  const handleUpload = async (e) => {
    e.preventDefault()
    setUploadError('')

    if (!title.trim()) {
      setUploadError('Meeting title is required')
      return
    }
    if (!selectedFile) {
      setUploadError('Please select a recording file to upload')
      return
    }

    const allowedExts = ['mp3', 'wav', 'm4a', 'ogg', 'webm', 'mp4', 'mov', 'avi', 'mkv']
    const ext = selectedFile.name.split('.').pop()?.toLowerCase() || ''
    if (!allowedExts.includes(ext)) {
      setUploadError(`Unsupported file type: .${ext}. Allowed: ${allowedExts.join(', ')}`)
      return
    }

    const maxSize = 500 * 1024 * 1024
    if (selectedFile.size > maxSize) {
      setUploadError('File too large. Maximum size is 500 MB.')
      return
    }

    try {
      setUploading(true)
      setUploadProgress(0)

      const formData = new FormData()
      formData.append('title', title.trim())
      if (description.trim()) formData.append('description', description.trim())
      formData.append('recording', selectedFile)

      const res = await api.post('/meetings', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (evt) => {
          if (evt.total > 0) {
            setUploadProgress(Math.round((evt.loaded * 100) / evt.total))
          }
        },
      })

      setUploading(false)
      setUploadProgress(100)
      setShowModal(false)
      setSuccessMsg(`Meeting "${res.data.title}" uploaded successfully. Processing will begin shortly.`)
      resetForm()
      loadMeetings()
    } catch (err) {
      setUploading(false)
      setUploadProgress(0)
      const detail = err.response?.data?.detail
      if (typeof detail === 'string') {
        setUploadError(detail)
      } else if (Array.isArray(detail)) {
        setUploadError(detail.map((d) => d.msg || JSON.stringify(d)).join('; '))
      } else {
        setUploadError('Upload failed. Please try again.')
      }
    }
  }

  const canUpload = !uploading && title.trim() && selectedFile

  const handleTranscribe = async (m) => {
    if (transcribingId) return
    try {
      setTranscribingId(m.id)
      setError('')
      const res = await api.post(`/meetings/${m.id}/transcribe`)
      setSuccessMsg(`Transcription completed for "${m.title}".`)
      setDetailMeeting(res.data)
      await loadMeetings()
    } catch (err) {
      const detail = err.response?.data?.detail
      if (typeof detail === 'string') setError(detail)
      else if (Array.isArray(detail)) setError(detail.map((d) => d.msg || JSON.stringify(d)).join('; '))
      else setError('Transcription failed. Please try again.')
      await loadMeetings()
    } finally {
      setTranscribingId(null)
    }
  }

  const handleAnalyze = async (m) => {
    if (analyzingId) return
    try {
      setAnalyzingId(m.id)
      setError('')
      const res = await api.post(`/meetings/${m.id}/analyze`)
      setSuccessMsg(`Analysis completed for "${m.title}".`)
      setDetailMeeting(res.data)
      await loadMeetings()
    } catch (err) {
      const detail = err.response?.data?.detail
      if (typeof detail === 'string') setError(detail)
      else if (Array.isArray(detail)) setError(detail.map((d) => d.msg || JSON.stringify(d)).join('; '))
      else setError('Analysis failed. Please try again.')
      await loadMeetings()
    } finally {
      setAnalyzingId(null)
    }
  }

  const handleViewDetail = async (m) => {
    try {
      const res = await api.get(`/meetings/${m.id}`)
      setDetailMeeting(res.data)
    } catch (err) {
      const detail = err.response?.data?.detail
      if (typeof detail === 'string') setError(detail)
      setDetailMeeting(m)
    }
  }

  const closeDetail = () => setDetailMeeting(null)

  return (
    <ManagerLayout>
      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold text-slate-900">Meetings</h2>
            <p className="mt-1 text-sm text-slate-500">
              Upload meeting recordings for AI-powered transcription and analysis.
            </p>
          </div>
          <button
            onClick={openModal}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-blue-600 text-white font-semibold shadow-sm hover:bg-blue-700 active:bg-blue-800 transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            Upload Meeting
          </button>
        </div>

        {successMsg && (
          <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 px-4 py-3 rounded-xl text-sm flex items-start gap-3">
            <svg className="w-5 h-5 flex-shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12"/></svg>
            <div>{successMsg}</div>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-xl text-sm flex items-start gap-3">
            <svg className="w-5 h-5 flex-shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
            <div>{error}</div>
          </div>
        )}

        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-200">
            <h3 className="font-semibold text-slate-800">Uploaded Meetings</h3>
            <p className="text-xs text-slate-500 mt-0.5">Recordings you have uploaded</p>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-20">
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600"></div>
            </div>
          ) : meetings.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 px-6 text-center">
              <div className="w-20 h-20 rounded-2xl bg-slate-100 flex items-center justify-center mb-4">
                <svg className="w-10 h-10 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3-3m0 0l3 3m-3-3v12" />
                </svg>
              </div>
              <h4 className="text-lg font-semibold text-slate-900">No meetings yet</h4>
              <p className="mt-1 text-sm text-slate-500 max-w-md">
                Upload your first meeting recording to get started. Once uploaded, the system will transcribe and analyze your meeting automatically.
              </p>
              <button
                onClick={openModal}
                className="mt-5 inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 text-white font-semibold text-sm hover:bg-blue-700 transition"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Upload Your First Meeting
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Meeting Title</th>
                    <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">File</th>
                    <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Size</th>
                    <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Uploaded Date</th>
                    <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Status</th>
                    <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {meetings.map((m) => (
                    <tr key={m.id} className="hover:bg-slate-50/60 transition">
                      <td className="px-6 py-4">
                        <div className="font-semibold text-slate-900">{m.title}</div>
                        {m.description && (
                          <div className="text-xs text-slate-500 mt-0.5 line-clamp-1">{m.description}</div>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2 text-sm">
                          <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center text-slate-500 flex-shrink-0">
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                              {m.content_type?.startsWith('video') ? (
                                <><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></>
                              ) : (
                                <><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></>
                              )}
                            </svg>
                          </div>
                          <div className="truncate max-w-[200px]" title={m.original_filename}>
                            <div className="text-slate-700">{m.original_filename}</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-sm text-slate-600">
                        {formatFileSize(m.file_size)}
                      </td>
                      <td className="px-6 py-4 text-sm text-slate-600 whitespace-nowrap">
                        {formatDate(m.created_at)}
                      </td>
                      <td className="px-6 py-4">
                        <StatusBadge status={m.status} />
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2">
                          {(m.status === 'uploaded' || m.status === 'failed') ? (
                            <button
                              title="Transcribe"
                              onClick={() => handleTranscribe(m)}
                              disabled={!!transcribingId || transcribingId === m.id}
                              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200 hover:bg-indigo-100 transition disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                              {transcribingId === m.id ? (
                                <>
                                  <svg className="w-3.5 h-3.5 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>
                                  Transcribing...
                                </>
                              ) : (
                                <>
                                  <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>
                                  Transcribe
                                </>
                              )}
                            </button>
                          ) : null}
                          {m.status === 'completed' && !hasAnalysis(m) && (
                            <button
                              title="Analyze with Gemini"
                              onClick={() => handleAnalyze(m)}
                              disabled={!!analyzingId || analyzingId === m.id}
                              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-fuchsia-50 text-fuchsia-700 border border-fuchsia-200 hover:bg-fuchsia-100 transition disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                              {analyzingId === m.id ? (
                                <>
                                  <svg className="w-3.5 h-3.5 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>
                                  Analyzing...
                                </>
                              ) : (
                                <>
                                  <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2z"/><path d="M12 8v4"/><path d="M12 16h.01"/></svg>
                                  Analyze
                                </>
                              )}
                            </button>
                          )}
                          <button
                            title="View details and transcript"
                            onClick={() => handleViewDetail(m)}
                            className="p-2 rounded-lg text-slate-500 hover:bg-slate-100 hover:text-slate-700 transition"
                          >
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
                            </svg>
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-slate-900">Upload Meeting Recording</h3>
                <p className="text-xs text-slate-500 mt-0.5">Audio and video formats supported</p>
              </div>
              <button
                onClick={closeModal}
                disabled={uploading}
                className="p-2 rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition disabled:opacity-40"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            </div>

            <form onSubmit={handleUpload} className="p-6 space-y-5">
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                  Meeting Title <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  disabled={uploading}
                  placeholder="e.g. Q4 Planning Review"
                  maxLength={500}
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-300 text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition disabled:bg-slate-50 disabled:text-slate-500"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                  Description <span className="text-slate-400 font-normal">(optional)</span>
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  disabled={uploading}
                  placeholder="Add context, agenda, or notes about this meeting..."
                  rows={3}
                  maxLength={5000}
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-300 text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition resize-none disabled:bg-slate-50 disabled:text-slate-500"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                  Recording File <span className="text-red-500">*</span>
                </label>
                <div
                  onClick={() => !uploading && fileInputRef.current?.click()}
                  className={`border-2 border-dashed rounded-xl p-6 text-center transition ${
                    selectedFile
                      ? 'border-blue-300 bg-blue-50/60 cursor-default'
                      : uploading
                      ? 'border-slate-200 bg-slate-50 cursor-not-allowed'
                      : 'border-slate-300 hover:border-blue-400 hover:bg-blue-50/30 cursor-pointer'
                  }`}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    onChange={handleFileChange}
                    disabled={uploading}
                    accept=".mp3,.wav,.m4a,.ogg,.webm,.mp4,.mov,.avi,.mkv,audio/*,video/*"
                    className="hidden"
                  />
                  <div className="flex flex-col items-center">
                    <div className={`w-12 h-12 rounded-xl flex items-center justify-center mb-3 ${selectedFile ? 'bg-blue-100 text-blue-600' : 'bg-slate-100 text-slate-400'}`}>
                      {selectedFile ? (
                        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                          <polyline points="20 6 9 17 4 12"/>
                        </svg>
                      ) : (
                        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                          <path d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
                        </svg>
                      )}
                    </div>
                    {selectedFile ? (
                      <div>
                        <div className="font-semibold text-slate-800 break-all">{selectedFile.name}</div>
                        <div className="text-xs text-slate-500 mt-1">
                          {formatFileSize(selectedFile.size)}
                        </div>
                      </div>
                    ) : (
                      <div>
                        <div className="text-sm font-semibold text-slate-700">
                          Click to select a file or drag and drop
                        </div>
                        <div className="text-xs text-slate-500 mt-1">
                          MP3, WAV, M4A, OGG, WEBM, MP4, MOV, AVI, MKV • Max 500 MB
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {uploading && (
                <div>
                  <div className="flex items-center justify-between text-xs text-slate-600 mb-1.5">
                    <span className="font-semibold">Uploading...</span>
                    <span className="font-semibold">{uploadProgress}%</span>
                  </div>
                  <div className="w-full bg-slate-200 rounded-full h-2.5 overflow-hidden">
                    <div
                      className="h-full bg-blue-600 transition-all duration-150 ease-out"
                      style={{ width: `${uploadProgress}%` }}
                    />
                  </div>
                </div>
              )}

              {uploadError && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl text-sm flex items-start gap-2.5">
                  <svg className="w-5 h-5 flex-shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                  <div>{uploadError}</div>
                </div>
              )}

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={closeModal}
                  disabled={uploading}
                  className="px-5 py-2.5 rounded-xl border border-slate-300 text-slate-700 font-semibold hover:bg-slate-50 transition disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!canUpload}
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-blue-600 text-white font-semibold shadow-sm hover:bg-blue-700 active:bg-blue-800 transition disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {uploading ? (
                    <>
                      <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>
                      Uploading...
                    </>
                  ) : (
                    <>
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                        <path d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
                      </svg>
                      Upload
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {detailMeeting && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl max-h-[85vh] overflow-hidden flex flex-col">
            <div className="px-6 py-4 border-b border-slate-200 flex items-start justify-between gap-4">
              <div className="min-w-0">
                <h3 className="text-lg font-bold text-slate-900 truncate">{detailMeeting.title}</h3>
                <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                  <span>{formatDate(detailMeeting.created_at)}</span>
                  <span>•</span>
                  <span>{formatFileSize(detailMeeting.file_size)}</span>
                  <span>•</span>
                  <StatusBadge status={detailMeeting.status} />
                </div>
                {detailMeeting.description && (
                  <p className="mt-2 text-sm text-slate-600">{detailMeeting.description}</p>
                )}
              </div>
              <button
                onClick={closeDetail}
                className="p-2 rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition flex-shrink-0"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            </div>
            <div className="p-6 overflow-y-auto space-y-8">
              <div>
                <div className="mb-4 text-xs text-slate-500 font-semibold uppercase tracking-wider">Transcript</div>
                {detailMeeting.status === 'uploaded' && (
                  <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                    This meeting has not been transcribed yet. Close this dialog and click <span className="font-semibold text-indigo-700">Transcribe</span>.
                  </div>
                )}
                {detailMeeting.status === 'processing' && (
                  <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700 flex items-center gap-2">
                    <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>
                    Transcription is in progress. Please wait...
                  </div>
                )}
                {detailMeeting.status === 'failed' && (
                  <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 flex items-center gap-2">
                    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                    Transcription failed. Click <span className="font-semibold">Transcribe</span> on the row above to retry.
                  </div>
                )}
                {detailMeeting.status === 'completed' && (
                  <>
                    {detailMeeting.transcript ? (
                      <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-4 whitespace-pre-wrap text-sm text-slate-800 leading-relaxed max-h-80 overflow-y-auto">
                        {detailMeeting.transcript}
                      </div>
                    ) : (
                      <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600 italic">
                        Transcription completed, but no speech was detected in the recording.
                      </div>
                    )}
                  </>
                )}
              </div>

              {detailMeeting.status === 'completed' && hasAnalysis(detailMeeting) && (
                <>
                  <div>
                    <div className="mb-3 text-xs text-slate-500 font-semibold uppercase tracking-wider">Summary</div>
                    <div className="rounded-xl border border-slate-200 bg-emerald-50/40 p-4 text-sm text-slate-800 leading-relaxed whitespace-pre-wrap">
                      {detailMeeting.summary}
                    </div>
                  </div>

                  <div>
                    <div className="mb-3 text-xs text-slate-500 font-semibold uppercase tracking-wider">Key Decisions</div>
                    {(() => {
                      const decisions = parseJSON(detailMeeting.key_decisions, [])
                      if (!Array.isArray(decisions) || decisions.length === 0) {
                        return (
                          <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-500 italic">
                            No key decisions identified.
                          </div>
                        )
                      }
                      return (
                        <ul className="rounded-xl border border-slate-200 bg-slate-50 divide-y divide-slate-100">
                          {decisions.map((d, i) => (
                            <li key={i} className="px-4 py-3 text-sm text-slate-800 flex gap-3">
                              <span className="mt-0.5 flex-shrink-0 w-5 h-5 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center text-xs font-bold">
                                {i + 1}
                              </span>
                              <span>{d}</span>
                            </li>
                          ))}
                        </ul>
                      )
                    })()}
                  </div>

                  <div>
                    <div className="mb-3 text-xs text-slate-500 font-semibold uppercase tracking-wider">Action Items</div>
                    {(() => {
                      const items = parseJSON(detailMeeting.action_items_json, [])
                      if (!Array.isArray(items) || items.length === 0) {
                        return (
                          <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-500 italic">
                            No action items identified.
                          </div>
                        )
                      }
                      return (
                        <div className="rounded-xl border border-slate-200 bg-white divide-y divide-slate-100 overflow-hidden">
                          {items.map((it, i) => (
                            <div key={i} className="px-4 py-4">
                              <div className="flex items-start gap-3">
                                <span className="mt-0.5 flex-shrink-0 w-6 h-6 rounded-lg bg-fuchsia-100 text-fuchsia-700 flex items-center justify-center text-xs font-bold">
                                  {i + 1}
                                </span>
                                <div className="flex-1 min-w-0">
                                  <div className="text-sm font-semibold text-slate-900">{it.task}</div>
                                  <div className="mt-2 flex flex-wrap gap-3 text-xs">
                                    {it.person && (
                                      <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-blue-50 text-blue-700 border border-blue-100">
                                        <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                                        <span className="font-medium">{it.person}</span>
                                      </div>
                                    )}
                                    {it.deadline && (
                                      <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-50 text-amber-700 border border-amber-100">
                                        <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
                                        <span className="font-medium">{it.deadline}</span>
                                      </div>
                                    )}
                                    {!it.person && !it.deadline && (
                                      <div className="text-slate-400 italic">No assignee or deadline specified.</div>
                                    )}
                                  </div>
                                </div>
                                <div className="flex-shrink-0">
                                  <button
                                    onClick={() => handleStartCreateTask(i, it)}
                                    disabled={creatingTaskIndex !== null || transcribingId !== null || analyzingId !== null || submittingTask}
                                    title="Assign to an employee and create a task"
                                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100 transition disabled:opacity-50 disabled:cursor-not-allowed"
                                  >
                                    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="19" y1="8" x2="19" y2="14"/><line x1="22" y1="11" x2="16" y2="11"/></svg>
                                    Assign
                                  </button>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )
                    })()}
                  </div>

                  <div className="mt-6">
                    <div className="mb-3 text-xs text-slate-500 font-semibold uppercase tracking-wider flex items-center justify-between">
                      <span>Linked Tasks ({linkedTasks.length})</span>
                    </div>
                    {linkedTasksLoading ? (
                      <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-5 flex items-center justify-center">
                        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
                      </div>
                    ) : linkedTasks.length === 0 ? (
                      <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-500 italic">
                        No tasks have been created from this meeting yet. Use Assign on the action items above.
                      </div>
                    ) : (
                      <div className="rounded-xl border border-slate-200 bg-white divide-y divide-slate-100 overflow-hidden">
                        {linkedTasks.map(t => (
                          <div key={t.id} className="px-4 py-3">
                            <div className="flex items-start justify-between gap-3">
                              <div className="min-w-0 flex-1">
                                <div className="text-sm font-semibold text-slate-900 truncate">{t.title}</div>
                                <div className="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500">
                                  <span className="inline-flex items-center gap-1.5">
                                    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                                      <circle cx="12" cy="7" r="4"/>
                                    </svg>
                                    {formatName(t.assigned_user)}
                                  </span>
                                  {t.deadline && (
                                    <span className="inline-flex items-center gap-1.5">
                                      <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                        <rect x="3" y="4" width="18" height="18" rx="2"/>
                                        <line x1="16" y1="2" x2="16" y2="6"/>
                                        <line x1="8" y1="2" x2="8" y2="6"/>
                                        <line x1="3" y1="10" x2="21" y2="10"/>
                                      </svg>
                                      Due {new Date(t.deadline).toLocaleDateString
                                        ? new Date(t.deadline).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
                                        : t.deadline}
                                    </span>
                                  )}
                                </div>
                              </div>
                              <div className="flex flex-wrap items-center gap-2 flex-shrink-0">
                                <TaskStatusBadge status={t.status} />
                                <TaskPriorityBadge priority={t.priority} />
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </>
              )}
            </div>
            <div className="px-6 py-3 border-t border-slate-200 flex items-center justify-end gap-3">
              <button
                onClick={closeDetail}
                className="px-5 py-2 rounded-xl border border-slate-300 text-slate-700 font-semibold hover:bg-slate-50 transition"
              >
                Close
              </button>
              {(detailMeeting.status === 'uploaded' || detailMeeting.status === 'failed') && (
                <button
                  onClick={() => { closeDetail(); handleTranscribe(detailMeeting) }}
                  disabled={!!transcribingId}
                  className="inline-flex items-center gap-2 px-5 py-2 rounded-xl bg-indigo-600 text-white font-semibold hover:bg-indigo-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>
                  {transcribingId === detailMeeting.id ? 'Transcribing...' : 'Transcribe'}
                </button>
              )}
              {detailMeeting.status === 'completed' && !hasAnalysis(detailMeeting) && (
                <button
                  onClick={() => { closeDetail(); handleAnalyze(detailMeeting) }}
                  disabled={!!analyzingId}
                  className="inline-flex items-center gap-2 px-5 py-2 rounded-xl bg-fuchsia-600 text-white font-semibold hover:bg-fuchsia-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2z"/><path d="M12 8v4"/><path d="M12 16h.01"/></svg>
                  {analyzingId === detailMeeting.id ? 'Analyzing...' : 'Analyze'}
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {creatingTaskIndex !== null && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-xl overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200 flex items-start justify-between gap-4">
              <div>
                <h3 className="text-lg font-bold text-slate-900">Create Task from Action Item #{creatingTaskIndex + 1}</h3>
                <p className="text-xs text-slate-500 mt-0.5">Review details, select an employee, and confirm.</p>
              </div>
              <button
                onClick={handleCloseTaskDialog}
                disabled={submittingTask}
                className="p-2 rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition disabled:opacity-40"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            </div>

            <div className="p-6 space-y-5 max-h-[70vh] overflow-y-auto">
              {taskSuccess && (
                <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 px-4 py-3 rounded-xl text-sm flex items-start gap-2.5">
                  <svg className="w-5 h-5 flex-shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12"/></svg>
                  <div>
                    <div className="font-semibold">{taskSuccess}</div>
                    {createdTask && (
                      <div className="text-emerald-700 text-xs mt-1">
                        Task ID #{createdTask.id} • Assigned to {formatName(createdTask.assigned_user) || 'selected employee'}
                      </div>
                    )}
                  </div>
                </div>
              )}
              {taskError && (
                <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-xl text-sm flex items-start gap-2.5">
                  <svg className="w-5 h-5 flex-shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                  <div>{taskError}</div>
                </div>
              )}

              {taskDraft.personReference && !taskSuccess && (
                <div className="rounded-xl border border-blue-100 bg-blue-50/70 px-4 py-3 text-sm">
                  <div className="text-xs font-semibold text-blue-700 uppercase tracking-wider mb-1">
                    AI Person Reference (hint only)
                  </div>
                  <div className="text-blue-900 font-medium flex items-center gap-2">
                    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>
                    "{taskDraft.personReference}" — This is a Gemini reference. You MUST explicitly select a registered employee below.
                  </div>
                </div>
              )}

              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                  Task Title <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={taskDraft.title}
                  onChange={(e) => setTaskDraft({ ...taskDraft, title: e.target.value })}
                  disabled={submittingTask || !!taskSuccess}
                  placeholder="e.g. Prepare quarterly financial report"
                  maxLength={500}
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-300 text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition disabled:bg-slate-50 disabled:text-slate-500"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                  Description <span className="text-slate-400 font-normal">(optional)</span>
                </label>
                <textarea
                  value={taskDraft.description}
                  onChange={(e) => setTaskDraft({ ...taskDraft, description: e.target.value })}
                  disabled={submittingTask || !!taskSuccess}
                  placeholder="Add context, deliverables, or additional details..."
                  rows={3}
                  maxLength={5000}
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-300 text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition resize-none disabled:bg-slate-50 disabled:text-slate-500"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                    Priority <span className="text-red-500">*</span>
                  </label>
                  <select
                    value={taskDraft.priority}
                    onChange={(e) => setTaskDraft({ ...taskDraft, priority: e.target.value })}
                    disabled={submittingTask || !!taskSuccess}
                    className="w-full px-4 py-2.5 rounded-xl border border-slate-300 text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition disabled:bg-slate-50 disabled:text-slate-500"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                    Deadline <span className="text-slate-400 font-normal">(optional)</span>
                  </label>
                  <input
                    type="date"
                    value={taskDraft.deadline}
                    onChange={(e) => setTaskDraft({ ...taskDraft, deadline: e.target.value })}
                    disabled={submittingTask || !!taskSuccess}
                    className="w-full px-4 py-2.5 rounded-xl border border-slate-300 text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition disabled:bg-slate-50 disabled:text-slate-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                  Assign to Registered Employee <span className="text-red-500">*</span>
                </label>
                {employees.length === 0 ? (
                  <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 flex items-center gap-2.5">
                    <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>
                    Loading employees...
                  </div>
                ) : (
                  <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                    {employees.map((emp) => {
                      const selected = String(taskDraft.assigned_to) === String(emp.id)
                      return (
                        <label
                          key={emp.id}
                          className={`flex items-center gap-3 p-3 rounded-xl border cursor-pointer transition ${
                            selected
                              ? 'border-blue-500 bg-blue-50/60 ring-1 ring-blue-200'
                              : 'border-slate-200 bg-white hover:bg-slate-50 hover:border-slate-300'
                          } ${(submittingTask || taskSuccess) ? 'opacity-70 cursor-not-allowed' : ''}`}
                        >
                          <input
                            type="radio"
                            name="task_assignee"
                            disabled={submittingTask || !!taskSuccess}
                            checked={selected}
                            onChange={() => setTaskDraft({ ...taskDraft, assigned_to: String(emp.id) })}
                            className="h-4 w-4 text-blue-600 focus:ring-blue-500"
                          />
                          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 text-white flex items-center justify-center font-bold text-sm flex-shrink-0">
                            {getInitials(emp)}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="text-sm font-semibold text-slate-900">{formatName(emp)}</div>
                            <div className="text-xs text-slate-500 truncate">{emp.email}</div>
                          </div>
                          {taskDraft.personReference && (
                            formatName(emp).toLowerCase().includes(taskDraft.personReference.toLowerCase()) ||
                            (emp.email || '').toLowerCase().includes(taskDraft.personReference.toLowerCase())
                          ) && (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-50 text-amber-700 border border-amber-200 uppercase tracking-wide">
                              Possible match
                            </span>
                          )}
                        </label>
                      )
                    })}
                  </div>
                )}
                {taskDraft.assigned_to && (
                  <div className="mt-2 text-xs text-emerald-700 font-medium inline-flex items-center gap-1">
                    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                    Employee selected.
                  </div>
                )}
              </div>
            </div>

            <div className="px-6 py-3 border-t border-slate-200 flex items-center justify-end gap-3 bg-slate-50">
              <button
                type="button"
                onClick={handleCloseTaskDialog}
                disabled={submittingTask}
                className="px-5 py-2 rounded-xl border border-slate-300 text-slate-700 font-semibold hover:bg-white transition disabled:opacity-40 disabled:cursor-not-allowed bg-white"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSubmitTask}
                disabled={submittingTask || !!taskSuccess || !taskDraft.title.trim() || !taskDraft.assigned_to}
                className="inline-flex items-center gap-2 px-5 py-2 rounded-xl bg-blue-600 text-white font-semibold shadow-sm hover:bg-blue-700 active:bg-blue-800 transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {submittingTask ? (
                  <>
                    <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>
                    Creating Task...
                  </>
                ) : taskSuccess ? (
                  <>
                    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                    Created
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                      <path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>
                    </svg>
                    Create Task
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </ManagerLayout>
  )
}
