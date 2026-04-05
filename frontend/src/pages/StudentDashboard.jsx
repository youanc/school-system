import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';

const StudentDashboard = () => {
  const [data, setData] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchGrades = async () => {
      try {
        const res = await api.get('/student/grades');
        setData(res.data);
      } catch (err) {
        alert("連線逾時或權限不足，請重新登入");
        navigate('/login');
      }
    };
    fetchGrades();
  }, [navigate]);

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };

  const requestPasswordReset = async () => {
    try {
      await api.post('/forgot-password', { email: data.email });
      alert("修改密碼信件已發送至您的信箱！");
    } catch (error) {
      alert("發送失敗");
    }
  };

  if (!data) return <div className="text-center mt-20">載入中...</div>;

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <div className="flex justify-between items-center mb-8 bg-white p-4 rounded shadow">
        <h1 className="text-2xl font-bold">
          學生專區 - 學號：{data.student_id} / 姓名： {data.name}
        </h1>
        <div>
          <button onClick={requestPasswordReset} className="bg-yellow-500 text-white px-4 py-2 rounded mr-2">修改密碼</button>
          <button onClick={handleLogout} className="bg-red-500 text-white px-4 py-2 rounded">登出</button>
        </div>
      </div>

      {/* 學生儀表板 - 成績列表改為橫向表格 */}
      <div className="bg-white rounded shadow overflow-hidden mt-6">
        <table className="w-full text-center border-collapse">
          <thead>
            <tr className="bg-gray-800 text-white">
              <th className="p-4 font-medium">國文</th>
              <th className="p-4 font-medium">英文</th>
              <th className="p-4 font-medium">數學</th>
              <th className="p-4 font-medium">物理</th>
              <th className="p-4 font-medium">化學</th>
            </tr>
          </thead>
          <tbody>
            {data.grades ? (
              <tr className="border-b hover:bg-gray-50">
                <td className="p-4 text-lg font-bold text-blue-600">{data.grades['國文']}</td>
                <td className="p-4 text-lg font-bold text-blue-600">{data.grades['英文']}</td>
                <td className="p-4 text-lg font-bold text-blue-600">{data.grades['數學']}</td>
                <td className="p-4 text-lg font-bold text-blue-600">{data.grades['物理']}</td>
                <td className="p-4 text-lg font-bold text-blue-600">{data.grades['化學']}</td>
              </tr>
            ) : (
              <tr>
                <td colSpan="5" className="p-6 text-gray-500">尚無成績紀錄</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default StudentDashboard;