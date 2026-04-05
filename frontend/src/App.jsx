import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import Login from './pages/Login';
import SetPassword from './pages/SetPassword';
import StudentDashboard from './pages/StudentDashboard';
import TeacherDashboard from './pages/TeacherDashboard';

// 30分鐘閒置登出 Hook
const useIdleTimeout = (onIdle, idleTime = 30 * 60 * 1000) => {
  useEffect(() => {
    let timeoutId;
    const resetTimer = () => {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(onIdle, idleTime);
    };

    const events = ['mousemove', 'keydown', 'scroll', 'click'];
    events.forEach(event => window.addEventListener(event, resetTimer));
    resetTimer();

    return () => {
      events.forEach(event => window.removeEventListener(event, resetTimer));
      clearTimeout(timeoutId);
    };
  }, [onIdle, idleTime]);
};

const Layout = () => {
  const navigate = useNavigate();
  const location = useLocation();

  // 執行閒置偵測 (如果在登入頁或設定密碼頁則不強制觸發)
  useIdleTimeout(() => {
    if (location.pathname !== '/login' && location.pathname !== '/set-password') {
      localStorage.removeItem('token');
      alert("閒置超過 30 分鐘，為了安全起見已將您登出。");
      navigate('/login');
    }
  });

  return (
    <div className="min-h-screen bg-gray-100 font-sans">
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/login" element={<Login />} />
        <Route path="/set-password" element={<SetPassword />} />
        <Route path="/student-dashboard" element={<StudentDashboard />} />
        <Route path="/teacher-dashboard" element={<TeacherDashboard />} />
      </Routes>
    </div>
  );
};

function App() {
  return (
    <Router>
      <Layout />
    </Router>
  );
}

export default App;