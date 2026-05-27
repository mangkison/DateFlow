import React, { useEffect, useState } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import LoginPage from "./pages/LoginPage";
import OnboardingPage from "./pages/OnboardingPage";
import ChatPage from "./pages/ChatPage";
import CourseResultPage from "./pages/CourseResultPage";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8001";

function PrivateRoute({ children }: { children: React.ReactElement }) {
  const { user } = useAuth();
  return user ? children : <Navigate to="/login" replace />;
}

// 로그인 상태일 때 취향 유무로 온보딩 vs 채팅 결정
function SmartHome() {
  const { user } = useAuth();
  const [dest, setDest] = useState<string | null>(null);

  useEffect(() => {
    if (!user) { setDest("/login"); return; }
    fetch(`${API}/prefs/${user.user_id}`, {
      headers: { Authorization: `Bearer ${user.token}` },
    })
      .then(r => setDest(r.ok ? "/chat" : "/onboarding"))
      .catch(() => setDest("/onboarding"));
  }, []);

  if (!dest) return null;
  return <Navigate to={dest} replace />;
}

function AppRoutes() {
  const { user } = useAuth();
  return (
    <Routes>
      <Route path="/login" element={user ? <SmartHome /> : <LoginPage />} />
      <Route path="/onboarding" element={<PrivateRoute><OnboardingPage /></PrivateRoute>} />
      <Route path="/chat" element={<PrivateRoute><ChatPage /></PrivateRoute>} />
      <Route path="/result" element={<PrivateRoute><CourseResultPage /></PrivateRoute>} />
      <Route path="/" element={<SmartHome />} />
      <Route path="*" element={<SmartHome />} />
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  );
}
