import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';

const StudentDashboard = () => {
  const [exams, setExams] = useState([]);
  const [selectedExamId, setSelectedExamId] = useState('');
  const [data, setData] = useState(null);
  const navigate = useNavigate();

  // 取得考試場次清單
  useEffect(() => {
    const fetchExams = async () => {
      try {
        const res = await api.get('/exams');
        setExams(res.data);
        if (res.data.length > 0) setSelectedExamId(res.data[0].id);
      } catch (err) {
        alert("連線逾時，請重新登入");
        navigate('/login');
      }
    };
    fetchExams();
  }, [navigate]);

  // 當選擇的考試改變時，拉取該場考試成績
  useEffect(() => {
    if (!selectedExamId) return;
    const fetchGrades = async () => {
      try {
        const res = await api.get(`/student/grades/${selectedExamId}`);
        setData(res.data);
      } catch (err) {
        console.error(err);
      }
    };
    fetchGrades();
  }, [selectedExamId]);

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };
// 👇 新增這段修改密碼的函數
  const requestPasswordReset = async () => {
    try {
      // 學生端已經有 data.email 的狀態了，直接拿來用
      await api.post('/forgot-password', { email: data.email });
      alert("修改密碼信件已發送至您的信箱！請前往收信。");
    } catch (error) {
      // 捕捉後端傳來的 60 秒冷卻提示或其他錯誤
      alert(error.response?.data?.msg || "發送失敗，請稍後再試");
    }
  };

  if (!data) return <div className="text-center mt-20">載入中...</div>;
  const subjects = data.grades ? Object.keys(data.grades) : [];

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="flex justify-between items-center mb-6 bg-white p-4 rounded shadow">
        <h1 className="text-2xl font-bold">
          學生專區 - 學號：{data.student_id} / 姓名： {data.name}
        </h1>
{/* 👇 這裡補上一個 div 將兩個按鈕包起來 */}
        <div>
          <button onClick={requestPasswordReset} className="bg-yellow-500 text-white px-4 py-2 rounded mr-2 hover:bg-yellow-600 transition">修改密碼</button>
          <button onClick={handleLogout} className="bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600 transition">登出</button>
        </div>
      </div>

      <div className="mb-6 flex items-center gap-4 bg-white p-4 rounded shadow">
        <label className="font-bold text-gray-700">選擇考試場次：</label>
        <select 
          className="border p-2 rounded focus:ring-2 focus:ring-blue-400"
          value={selectedExamId} 
          onChange={(e) => setSelectedExamId(e.target.value)}
        >
          {exams.map(exam => (
            <option key={exam.id} value={exam.id}>{exam.name}</option>
          ))}
        </select>
      </div>

      {data.grades ? (
        <div className="space-y-6">
          {/* 個人成績與排名 */}
          <div className="bg-white rounded shadow overflow-hidden">
            <div className="bg-gray-800 p-3 text-white flex justify-between px-6 items-center">
              <span className="font-bold">個人成績總覽</span>
              <span>總分: {data.total} | 平均: {data.average} | 班排名: {data.rank} / {data.total_students}</span>
            </div>
            <table className="w-full text-center border-collapse">
              <thead>
                <tr className="bg-gray-100 border-b">
                  {subjects.map(sub => <th key={sub} className="p-4 font-medium">{sub}</th>)}
                </tr>
              </thead>
              <tbody>
                <tr className="hover:bg-gray-50">
                  {subjects.map(sub => (
                    <td key={sub} className="p-4 text-lg font-bold text-blue-600">{data.grades[sub]}</td>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>

          {/* 全班五標資訊 */}
          <div className="bg-white rounded shadow overflow-hidden">
             <div className="bg-blue-600 p-3 text-white px-6 font-bold">全班五標與平均</div>
             <table className="w-full text-center border-collapse">
               <thead>
                 <tr className="bg-gray-100 border-b text-sm">
                   <th className="p-3">科目</th>
                   <th className="p-3 text-green-700">頂標 (88%)</th>
                   <th className="p-3 text-blue-700">前標 (75%)</th>
                   <th className="p-3 text-yellow-600">均標 (50%)</th>
                   <th className="p-3 text-orange-600">後標 (25%)</th>
                   <th className="p-3 text-red-600">底標 (12%)</th>
                   <th className="p-3 text-gray-700">全班平均</th>
                 </tr>
               </thead>
               <tbody>
                 {subjects.map(sub => {
                   // 預先取出該科目的標準資料，避免重複寫很長的 data.standards[sub]
                   const std = data.standards[sub] || {};
                   return (
                     <tr key={sub} className="border-b hover:bg-gray-50 text-sm">
                       <td className="p-3 font-bold">{sub}</td>
                       {/* 使用 Number().toFixed(2) 強制顯示兩位小數 */}
                       <td className="p-3">{Number(std['頂標'] || 0).toFixed(2)}</td>
                       <td className="p-3">{Number(std['前標'] || 0).toFixed(2)}</td>
                       <td className="p-3">{Number(std['均標'] || 0).toFixed(2)}</td>
                       <td className="p-3">{Number(std['後標'] || 0).toFixed(2)}</td>
                       <td className="p-3">{Number(std['底標'] || 0).toFixed(2)}</td>
                       <td className="p-3 bg-gray-50 font-bold">{Number(std['平均'] || 0).toFixed(2)}</td>
                     </tr>
                   );
                 })}
               </tbody>
             </table>
          </div>
        </div>
      ) : (
        <div className="bg-white p-8 text-center text-gray-500 rounded shadow">尚無此場考試成績</div>
      )}
    </div>
  );
};

export default StudentDashboard;