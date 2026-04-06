import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [cooldown, setCooldown] = useState(0); // [新增] CD 倒數狀態
  const navigate = useNavigate();

  // [新增] 元件載入時，檢查 localStorage 是否還有未過期的 CD
  useEffect(() => {
    const savedTime = localStorage.getItem('emailCooldownTime');
    if (savedTime) {
      const passedTime = Math.floor((Date.now() - parseInt(savedTime)) / 1000);
      if (passedTime < 60) {
        setCooldown(60 - passedTime);
      } else {
        localStorage.removeItem('emailCooldownTime');
      }
    }
  }, []);

  // [新增] 倒數計時器邏輯
  useEffect(() => {
    if (cooldown > 0) {
      const timer = setTimeout(() => setCooldown(cooldown - 1), 1000);
      return () => clearTimeout(timer);
    } else {
      localStorage.removeItem('emailCooldownTime');
    }
  }, [cooldown]);

  // [新增] 啟動 CD 的輔助函數
  const startCooldown = () => {
    setCooldown(60);
    localStorage.setItem('emailCooldownTime', Date.now().toString());
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const response = await api.post('/login', { email, password });
      localStorage.setItem('token', response.data.access_token);
      localStorage.setItem('userEmail', email); 
      
      if (response.data.role === 'teacher') navigate('/teacher-dashboard');
      else navigate('/student-dashboard');
      
    } catch (error) {
      if (error.response?.status === 403) {
        startCooldown(); // [新增] 觸發首次登入寄信，啟動 CD
        alert("此帳號尚未驗證或需重設密碼，已發送驗證信至您的 Email，請點擊連結設定密碼。");
      } else if (error.response?.status === 429) {
        // [新增] 攔截後端的 429 錯誤
        alert(error.response?.data?.msg || "請求太頻繁，請稍後再試");
      } else {
        alert(error.response?.data?.msg || "登入失敗");
      }
    }
  };

  const handleForgotPassword = async () => {
    if (!email) return alert("請先輸入您的 Email 帳號");
    if (cooldown > 0) return alert(`請等待 ${cooldown} 秒後再發送`); // [新增] 阻擋連點
    
    try {
      await api.post('/forgot-password', { email });
      startCooldown(); // [新增] 忘記密碼寄信成功，啟動 CD
      alert("密碼重設信已寄出，請至信箱收取。");
    } catch (error) {
      if (error.response?.status === 429) {
        // [新增] 攔截後端的 429 錯誤
        alert(error.response?.data?.msg || "請求太頻繁，請稍後再試");
      } else {
        alert("寄送失敗");
      }
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-200">
      <form onSubmit={handleLogin} className="p-8 bg-white rounded-lg shadow-lg w-96">
        <h2 className="text-2xl mb-6 font-bold text-center text-gray-800">校園成績管理系統</h2>
        <input 
          type="email" placeholder="輸入 Email" required
          className="w-full mb-4 p-3 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
          onChange={e => setEmail(e.target.value)} 
        />
        <input 
          type="password" placeholder="輸入密碼 (首次登入請留空)" 
          className="w-full mb-4 p-3 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
          onChange={e => setPassword(e.target.value)} 
        />
        <button type="submit" className="w-full bg-blue-600 text-white p-3 rounded hover:bg-blue-700 transition">
          登入
        </button>
        
        {/* [修改] 根據 CD 狀態改變按鈕樣式與可點擊性 */}
        <button 
          type="button" 
          onClick={handleForgotPassword} 
          disabled={cooldown > 0}
          className={`w-full mt-4 text-sm ${cooldown > 0 ? 'text-gray-400 cursor-not-allowed' : 'text-blue-500 hover:underline'}`}
        >
          {cooldown > 0 ? `請等待 ${cooldown} 秒後可再次寄信` : '忘記密碼 / 重新發送修改密碼信'}
        </button>
      </form>
    </div>
  );
};

export default Login;