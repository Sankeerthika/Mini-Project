import EmployeeLayout from '../../layouts/EmployeeLayout'
import { useAuth } from '../../context/AuthContext'

export default function EmployeeProfile() {
  const { user } = useAuth()

  const RoleBadge = ({ role }) => {
    const styles = {
      admin: 'bg-purple-100 text-purple-800',
      manager: 'bg-blue-100 text-blue-800',
      employee: 'bg-green-100 text-green-800',
    }
    return (
      <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold capitalize ${styles[role]}`}>
        {role}
      </span>
    )
  }

  return (
    <EmployeeLayout>
      <div className="max-w-3xl">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">My Profile</h2>
          <p className="mt-1 text-sm text-slate-500">View your account information</p>
        </div>

        <div className="mt-6 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="h-32 bg-gradient-to-br from-emerald-500 via-teal-500 to-cyan-500"></div>
          <div className="px-8 pb-8">
            <div className="flex flex-wrap items-end justify-between gap-4 -mt-14">
              <div className="flex items-end gap-5">
                <div className="w-28 h-28 rounded-2xl bg-white shadow-lg ring-4 ring-white flex items-center justify-center">
                  <div className="w-24 h-24 rounded-2xl bg-gradient-to-br from-emerald-400 to-teal-500 flex items-center justify-center text-white font-bold text-3xl">
                    {user?.first_name?.charAt(0)}{user?.last_name?.charAt(0)}
                  </div>
                </div>
                <div className="pb-2">
                  <h3 className="text-2xl font-bold text-slate-900">
                    {user?.first_name} {user?.last_name}
                  </h3>
                  <p className="text-slate-500 mt-0.5">{user?.email}</p>
                </div>
              </div>
              {user && <RoleBadge role={user.role} />}
            </div>

            <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-1">
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">First name</p>
                <p className="text-slate-900 font-medium">{user?.first_name}</p>
              </div>
              <div className="space-y-1">
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Last name</p>
                <p className="text-slate-900 font-medium">{user?.last_name}</p>
              </div>
              <div className="space-y-1">
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Email</p>
                <p className="text-slate-900 font-medium">{user?.email}</p>
              </div>
              <div className="space-y-1">
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Role</p>
                <p className="text-slate-900 font-medium capitalize">{user?.role}</p>
              </div>
              <div className="space-y-1">
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Account Status</p>
                <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium ${
                  user?.is_active ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-200 text-slate-600'
                }`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${user?.is_active ? 'bg-emerald-500' : 'bg-slate-400'}`}></span>
                  {user?.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
              <div className="space-y-1">
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Account created</p>
                <p className="text-slate-900 font-medium">
                  {user?.created_at ? new Date(user.created_at).toLocaleString() : '—'}
                </p>
              </div>
            </div>

            <div className="mt-8 p-4 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-600">
              <p className="font-medium text-slate-700 mb-1">🔒 Security Notice</p>
              <p>Profile editing and password change features will be available in a future update. Contact your manager or an administrator if you need to change your account details.</p>
            </div>
          </div>
        </div>
      </div>
    </EmployeeLayout>
  )
}
