import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import Login from './pages/Login'
import ProtectedRoute from './components/ProtectedRoute'
import AdminDashboard from './pages/admin/Dashboard'
import AdminUsers from './pages/admin/Users'
import AdminProfile from './pages/admin/Profile'
import ManagerDashboard from './pages/manager/Dashboard'
import ManagerMeetings from './pages/manager/Meetings'
import ManagerTasks from './pages/manager/Tasks'
import ManagerTeam from './pages/manager/Team'
import ManagerProfile from './pages/manager/Profile'
import EmployeeDashboard from './pages/employee/Dashboard'
import EmployeeTasks from './pages/employee/Tasks'
import EmployeeProfile from './pages/employee/Profile'

function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="min-h-screen bg-gray-50">
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/" element={<Navigate to="/login" replace />} />

            <Route element={<ProtectedRoute allowedRoles={['admin']} />}>
              <Route path="/admin" element={<AdminDashboard />} />
              <Route path="/admin/users" element={<AdminUsers />} />
              <Route path="/admin/profile" element={<AdminProfile />} />
            </Route>

            <Route element={<ProtectedRoute allowedRoles={['manager']} />}>
              <Route path="/manager" element={<ManagerDashboard />} />
              <Route path="/manager/meetings" element={<ManagerMeetings />} />
              <Route path="/manager/tasks" element={<ManagerTasks />} />
              <Route path="/manager/team" element={<ManagerTeam />} />
              <Route path="/manager/profile" element={<ManagerProfile />} />
            </Route>

            <Route element={<ProtectedRoute allowedRoles={['employee']} />}>
              <Route path="/employee" element={<EmployeeDashboard />} />
              <Route path="/employee/tasks" element={<EmployeeTasks />} />
              <Route path="/employee/profile" element={<EmployeeProfile />} />
            </Route>

            <Route path="*" element={<Navigate to="/login" replace />} />
          </Routes>
        </div>
      </Router>
    </AuthProvider>
  )
}

export default App
