import { useState } from 'react'
import { useNavigate, useLocation, Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Login() {
  const { login, isAuthenticated, user, loading } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const [email, setEmail] = useState('admin@example.com')
  const [password, setPassword] = useState('Admin123!')
  const [error, setError] = useState(() => {
    const params = new URLSearchParams(window.location.search)
    if (params.get('reason') === 'deactivated') {
      return 'Your account has been deactivated. Contact an administrator.'
    }
    return ''
  })
  const [mode, setMode] = useState('login')
  const [registerRole, setRegisterRole] = useState('employee')
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')

  if (isAuthenticated) {
    const from = location.state?.from?.pathname
    if (from) {
      return <Navigate to={from} replace />
    }
    if (user?.role === 'admin') {
      return <Navigate to="/admin" replace />
    }
    if (user?.role === 'manager') {
      return <Navigate to="/manager" replace />
    }
    if (user?.role === 'employee') {
      return <Navigate to="/employee" replace />
    }
  }

  const redirectAfterRole = (role) => {
    if (role === 'admin') navigate('/admin')
    else if (role === 'manager') navigate('/manager')
    else if (role === 'employee') navigate('/employee')
    else navigate('/login')
  }

  const handleLogin = async (e) => {
    e.preventDefault()
    setError('')
    try {
      const { user } = await login(email, password)
      redirectAfterRole(user.role)
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed. Please try again.')
    }
  }



  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-indigo-900 to-slate-900 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8 bg-white/95 backdrop-blur rounded-2xl shadow-2xl p-8">
        <div>
          <div className="mx-auto h-14 w-14 flex items-center justify-center rounded-full bg-indigo-100 mb-4">
            <svg className="h-8 w-8 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          </div>
          <h2 className="mt-2 text-center text-3xl font-extrabold text-slate-900">
            AI Meeting Intelligence
          </h2>
          <p className="mt-2 text-center text-sm text-slate-600">
            {mode === 'login' ? 'Sign in to your account' : 'Create a new account'}
          </p>
        </div>

        <div className="flex border border-slate-200 rounded-lg p-1 bg-slate-50">
          <button
            type="button"
            onClick={() => setMode('login')}
            className={`flex-1 py-2 px-3 rounded-md text-sm font-medium transition ${
              mode === 'login'
                ? 'bg-white text-indigo-700 shadow-sm border border-slate-200'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => {
              setMode('register')
              setError('')
            }}
            className={`flex-1 py-2 px-3 rounded-md text-sm font-medium transition ${
              mode === 'register'
                ? 'bg-white text-indigo-700 shadow-sm border border-slate-200'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Register
          </button>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
            {error}
          </div>
        )}

        {mode === 'login' ? (
          <form className="mt-8 space-y-6" onSubmit={handleLogin}>
            <div className="space-y-4">
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-slate-700 mb-1">
                  Email address
                </label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="appearance-none relative block w-full px-3 py-2.5 border border-slate-300 placeholder-slate-400 text-slate-900 rounded-lg focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                  placeholder="you@example.com"
                />
              </div>
              <div>
                <label htmlFor="password" className="block text-sm font-medium text-slate-700 mb-1">
                Password
              </label>
                <input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="appearance-none relative block w-full px-3 py-2.5 border border-slate-300 placeholder-slate-400 text-slate-900 rounded-lg focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                  placeholder="••••••••"
                />
              </div>
            </div>

            <div>
              <button
                type="submit"
                disabled={loading}
                className="group relative w-full flex justify-center py-2.5 px-4 border border-transparent text-sm font-medium rounded-lg text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition"
              >
                {loading ? 'Signing in...' : 'Sign In'}
              </button>
            </div>
          </form>
        ) : (
          <RegisterForm
            firstName={firstName} setFirstName={setFirstName}
            lastName={lastName} setLastName={setLastName}
            email={email} setEmail={setEmail}
            password={password} setPassword={setPassword}
            registerRole={registerRole} setRegisterRole={setRegisterRole}
            error={error} setError={setError}
            loading={loading}
          />
        )}

        <div className="mt-6 text-xs text-slate-500 bg-slate-50 rounded-lg p-3 border border-slate-200 space-y-2">
          <div>
            <p className="font-semibold text-slate-700 mb-1">🔐 All demo accounts share the same password:</p>
            <p className="font-mono text-slate-800 font-semibold bg-white border border-slate-200 rounded px-2 py-1 inline">Admin123!</p>
          </div>
          <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-200">
            <div>
              <p className="font-semibold text-purple-700">Admin</p>
              <p className="font-mono text-[11px]">admin@example.com</p>
            </div>
            <div>
              <p className="font-semibold text-blue-700">Manager</p>
              <p className="font-mono text-[11px]">manager@example.com</p>
            </div>
            <div>
              <p className="font-semibold text-emerald-700">Employee</p>
              <p className="font-mono text-[11px]">employee@example.com</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function RegisterForm(props) {
  const {
    firstName, setFirstName,
    lastName, setLastName,
    email, setEmail,
    password, setPassword,
    registerRole, setRegisterRole,
    setError,
    loading,
  } = props

  const { register } = useAuth()
  const navigate = useNavigate()

  const onSubmit = async (e) => {
    e.preventDefault()
    setError('')
    try {
      await register({
        first_name: firstName,
        last_name: lastName,
        email,
        password,
        role: registerRole,
      })
      alert('Registration successful! Please sign in.')
    } catch (err) {
      setError(err.response?.data?.detail || 'Registration failed.')
      return
    }
    navigate('/login')
  }

  return (
    <form className="mt-8 space-y-4" onSubmit={onSubmit}>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">First name</label>
          <input
            required
            value={firstName}
            onChange={(e) => setFirstName(e.target.value)}
            className="w-full px-3 py-2.5 border border-slate-300 rounded-lg focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            placeholder="Jane"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Last name</label>
          <input
            required
            value={lastName}
            onChange={(e) => setLastName(e.target.value)}
            className="w-full px-3 py-2.5 border border-slate-300 rounded-lg focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            placeholder="Doe"
          />
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">Email</label>
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full px-3 py-2.5 border border-slate-300 rounded-lg focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
          placeholder="you@example.com"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">Password</label>
        <input
          type="password"
          required
          minLength={6}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full px-3 py-2.5 border border-slate-300 rounded-lg focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
          placeholder="At least 6 characters"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">Role</label>
        <div className="grid grid-cols-2 gap-3">
          {[
            { value: 'employee', label: 'Employee', desc: 'View assigned tasks' },
            { value: 'manager', label: 'Manager', desc: 'Upload meetings' },
          ].map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => setRegisterRole(opt.value)}
              className={`p-3 border rounded-lg text-left transition ${
                registerRole === opt.value
                  ? 'border-indigo-500 bg-indigo-50 ring-2 ring-indigo-100'
                  : 'border-slate-200 hover:border-slate-300'
              }`}
            >
              <div className="font-semibold text-sm text-slate-800">{opt.label}</div>
              <div className="text-xs text-slate-500 mt-0.5">{opt.desc}</div>
            </button>
          ))}
        </div>
        <p className="mt-2 text-xs text-amber-700 bg-amber-50 px-2 py-1.5 rounded border border-amber-200 mt-2">
          ⚠️ Admin accounts can only be created by existing administrators or via the setup script.
        </p>
      </div>

      <div>
        <button
          type="submit"
          disabled={loading}
          className="group relative w-full flex justify-center py-2.5 px-4 border border-transparent text-sm font-medium rounded-lg text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 transition"
        >
          {loading ? 'Creating account...' : 'Create Account'}
        </button>
      </div>
    </form>
  )
}
