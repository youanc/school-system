import React, { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios'; // 這裡直接用 axios 避免攔截器蓋掉 token

const SetPassword = () => {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  const navigate = useNavigate();
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const handleSetPassword = async (e) => {
    e.preventDefault();
    if (password !== confirmPassword) return alert("兩次密碼輸入不一致");
    
    // 密碼規則驗證：至少8碼，英數字與特殊符號
    const strongRegex = new RegExp("^(?=.*[a-zA-Z])(?=.*\\d)(?=.*[\\W_]).{8,}$");
    if (!strongRegex.test(password)) {
      return alert("密碼必須包含英數字與特殊符號，且至少8碼");
    }

    try {
      await axios.post('http://127.0.0.1:5000/set-password', 
        { password },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      alert("密碼設定成功，請重新登入！");
      navigate('/login');
    } catch (error) {
      alert(error.response?.data?.msg || "Token 無效或已過期，請重新索取。");
    }
  };

  if (!token) return <div className="text-center mt-20">無效的連結</div>;

  return (
    <div className="flex flex-col items-center justify-center min-h-screen">
      <form onSubmit={handleSetPassword} className="p-8 bg-white rounded shadow-md w-96">
        <h2 className="text-xl mb-4 font-bold text-center">設定新密碼</h2>
        <input 
          type="password" placeholder="新密碼" required
          className="w-full mb-4 p-2 border rounded"
          onChange={e => setPassword(e.target.value)} 
        />
        <input 
          type="password" placeholder="確認新密碼" required
          className="w-full mb-4 p-2 border rounded"
          onChange={e => setConfirmPassword(e.target.value)} 
        />
        <button type="submit" className="w-full bg-green-500 text-white p-2 rounded">
          確認設定
        </button>
      </form>
    </div>
  );
};

export default SetPassword;