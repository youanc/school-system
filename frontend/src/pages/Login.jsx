import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const response = await api.post('/login', { email, password });
      localStorage.setItem('token', response.data.access_token);
      localStorage.setItem('userEmail', email); // 儲存 Email 供修改密碼使用
      
      if (response.data.role === 'teacher') navigate('/teacher-dashboard');
      else navigate('/student-dashboard');
      
    } catch (error) {
      if (error.response?.status === 403) {
        alert("此帳號尚未驗證或需重設密碼，已發送驗證信至您的 Email，請點擊連結設定密碼。");
      } else {
        alert(error.response?.data?.msg || "登入失敗");
      }
    }
  };

  const handleForgotPassword = async () => {
    if (!email) return alert("請先輸入您的 Email 帳號");
    try {
      await api.post('/forgot-password', { email });
      alert("密碼重設信已寄出，請至信箱收取。");
    } catch (error) {
      alert("寄送失敗");
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
        <button type="button" onClick={handleForgotPassword} className="w-full mt-4 text-sm text-blue-500 hover:underline">
          忘記密碼 / 重新發送修改密碼信
        </button>
      </form>
    </div>
  );
};

export default Login;