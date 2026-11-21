import { createContext, useContext, useState, useEffect, useMemo } from 'react'
import api from '../services/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('user')
    return saved ? JSON.parse(saved) : null
  })
  const [token, setToken] = useState(() => localStorage.getItem('token') || null)
  const [loading, setLoading] = useState(false)
  const [validating, setValidating] = useState(() => !!localStorage.getItem('token'))

  useEffect(() => {
    const storedToken = localStorage.getItem('token')
    if (storedToken) {
      setValidating(true)
      api.get('/auth/me')
        .then((res) => {
          setUser(res.data)
          localStorage.setItem('user', JSON.stringify(res.data))
        })
        .catch(() => {
          localStorage.removeItem('token')
          localStorage.removeItem('user')
          setToken(null)
          setUser(null)
        })
        .finally(() => {
          setValidating(false)
        })
    } else {
      setValidating(false)
    }
  }, [])

  const login = async (email, password) => {
    setLoading(true)
    try {
      const formData = new URLSearchParams()
      formData.append('username', email)
      formData.append('password', password)

      const response = await api.post('/auth/login', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      })

      const { access_token, user } = response.data
      setToken(access_token)
      setUser(user)
      localStorage.setItem('token', access_token)
      localStorage.setItem('user', JSON.stringify(user))
      return { user, token: access_token }
    } finally {
      setLoading(false)
    }
  }

  const register = async (userData) => {
    setLoading(true)
    try {
      const response = await api.post('/auth/register', userData)
      return response.data
    } finally {
      setLoading(false)
    }
  }

  const logout = () => {
    setUser(null)
    setToken(null)
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  const isAuthenticated = !!token && !!user

  const hasRole = (role) => isAuthenticated && user?.role === role

  const value = useMemo(
    () => ({
      user,
      token,
      loading,
      validating,
      login,
      register,
      logout,
      isAuthenticated,
      hasRole,
      setUser,
    }),
    [user, token, loading, validating]
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
