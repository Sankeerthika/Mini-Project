import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function ProtectedRoute({ allowedRoles }) {
  const { isAuthenticated, user, loading, validating } = useAuth()
  const location = useLocation()

  if (loading || validating) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  if (allowedRoles && user && !allowedRoles.includes(user.role)) {
    const defaultRoute = user.role === 'admin' ? '/admin' : user.role === 'manager' ? '/manager' : '/employee'
    return <Navigate to={defaultRoute} replace />
  }

  return <Outlet />
}
