import React from 'react';
import { AuthProvider, useAuth } from './auth/AuthProvider';
import { LoginForm } from './auth/LoginForm';
import { ChatAssistant } from './components/chat/ChatAssistant';
import { Shield, LogOut } from 'lucide-react';

function MainPortal() {
  const { user, loading, logout } = useAuth();

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-50 text-sm text-gray-500">
        Loading...
      </div>
    );
  }

  if (!user) {
    return <LoginForm />;
  }

  return (
    <ChatAssistant
      headerActions={
        <>
          <span className="text-xs font-semibold text-gray-600 bg-gray-50 px-2.5 py-1.5 rounded-lg border border-gray-200 shadow-sm">
            👤 {user.username} ({user.role})
          </span>
          {user.role === 'admin' && (
            <a
              href="/admin.html"
              className="flex items-center gap-1 text-xs font-semibold text-skred bg-red-50 hover:bg-red-100 border border-red-200 px-2.5 py-1.5 rounded-lg shadow-sm transition"
            >
              <Shield className="h-3.5 w-3.5" />
              관리자 콘솔
            </a>
          )}
          <button
            type="button"
            onClick={logout}
            className="flex items-center gap-1 text-xs font-semibold text-gray-600 bg-white hover:bg-gray-100 border border-gray-200 px-2.5 py-1.5 rounded-lg shadow-sm transition"
          >
            <LogOut className="h-3.5 w-3.5" />
            로그아웃
          </button>
        </>
      }
    />
  );
}

export default function App() {
  return (
    <AuthProvider>
      <MainPortal />
    </AuthProvider>
  );
}
