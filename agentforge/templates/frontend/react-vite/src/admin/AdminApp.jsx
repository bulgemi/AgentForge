import React from 'react';
import { AuthProvider, useAuth } from '../auth/AuthProvider';
import { LoginForm } from '../auth/LoginForm';
import { AccountManagementPanel } from '../components/settings/AccountManagementPanel';
import { ShieldAlert, ArrowLeft, LogOut } from 'lucide-react';

function AdminConsole() {
  const { user, loading, logout } = useAuth();

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-50 text-sm text-gray-500">
        Loading...
      </div>
    );
  }

  if (!user) {
    return <LoginForm onLoginSuccess={() => window.location.reload()} />;
  }

  if (user.role !== 'admin') {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 p-6">
        <div className="w-full max-w-md rounded-2xl border border-gray-200 bg-white p-8 text-center shadow-lg">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-red-50 text-skred">
            <ShieldAlert className="h-8 w-8" />
          </div>
          <h2 className="text-xl font-bold text-gray-900 mb-2">관리자 접근 권한 없음</h2>
          <p className="text-sm text-gray-600 mb-6">
            현재 계정(<strong>{user.username}</strong>)은 시스템 관리자(Admin) 권한이 없습니다.
          </p>
          <div className="flex gap-3 justify-center">
            <a
              href="/"
              className="flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50"
            >
              <ArrowLeft className="h-4 w-4" />
              채팅 포털로 돌아가기
            </a>
            <button
              type="button"
              onClick={logout}
              className="flex items-center gap-1.5 rounded-lg bg-gray-900 px-4 py-2 text-sm font-semibold text-white hover:bg-gray-800"
            >
              <LogOut className="h-4 w-4" />
              로그아웃
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Admin GNB Header */}
      <header className="flex h-16 items-center justify-between border-b border-gray-200 bg-white px-8 shadow-sm">
        <div className="flex items-center gap-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-skred to-skorange text-white shadow-sm font-bold">
            ⚡
          </div>
          <div>
            <h1 className="text-base font-bold text-gray-900">{{ project_name }} - Admin Console</h1>
            <p className="text-xs text-gray-500">Security & Account Governance</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <a
            href="/"
            className="flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-xs font-semibold text-gray-700 hover:bg-gray-50"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            사용자 채팅 포털
          </a>
          <button
            type="button"
            onClick={logout}
            className="flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-xs font-semibold text-gray-700 hover:bg-gray-50"
          >
            <LogOut className="h-3.5 w-3.5" />
            로그아웃
          </button>
        </div>
      </header>

      {/* Main Admin Body */}
      <main className="mx-auto max-w-7xl py-8">
        <AccountManagementPanel />
      </main>
    </div>
  );
}

export default function AdminApp() {
  return (
    <AuthProvider>
      <AdminConsole />
    </AuthProvider>
  );
}
