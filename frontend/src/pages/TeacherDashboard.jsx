import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';

const TeacherDashboard = () => {
  const [students, setStudents] = useState([]);
  const [file, setFile] = useState(null);
  const [editingStudent, setEditingStudent] = useState(null);
  const navigate = useNavigate();

  // --- 姓名隱碼函數 ---
  const maskName = (name) => {
    if (!name) return "";
    if (name.length <= 2) return name[0] + "O";
    return name[0] + "O".repeat(name.length - 2) + name[name.length - 1];
  };

  // --- Email 隱碼函數 (保留前2碼，小老鼠前面變星號) ---
  const maskEmail = (email) => {
    if (!email) return "";
    const [local, domain] = email.split('@');
    if (!domain) return email;
    if (local.length <= 2) return local[0] + "***@" + domain;
    return local.substring(0, 2) + "****@" + domain;
  };

  const fetchStudents = async () => {
    try {
      const res = await api.get('/teacher/students');
      setStudents(res.data);
    } catch (err) {
      alert("連線逾時，請重新登入");
      navigate('/login');
    }
  };

  useEffect(() => {
    fetchStudents();
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };

  const requestPasswordReset = async () => {
    const email = localStorage.getItem('userEmail');
    await api.post('/forgot-password', { email });
    alert("修改密碼信件已發送至您的信箱！");
  };

  // Excel 匯入
  const handleImport = async () => {
    if (!file) return alert("請先選擇 Excel 檔案");
    const formData = new FormData();
    formData.append('file', file);
    try {
      await api.post('/teacher/import-grades', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      alert("成績匯入成功");
      fetchStudents();
    } catch (err) {
      alert("匯入失敗");
    }
  };

  // Excel 匯出
  const handleExport = async () => {
    try {
      const res = await api.get('/teacher/export-grades', { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'students_grades.xlsx');
      document.body.appendChild(link);
      link.click();
    } catch (err) {
      alert("匯出失敗");
    }
  };

  // 更新成績
  const handleUpdate = async (e) => {
    e.preventDefault();
    try {
      await api.put(`/teacher/students/${editingStudent.id}`, editingStudent);
      alert("更新成功");
      setEditingStudent(null);
      fetchStudents();
    } catch (err) {
      alert("更新失敗");
    }
  };

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="flex justify-between items-center mb-6 bg-white p-4 rounded shadow">
        <h1 className="text-2xl font-bold">教師管理後台</h1>
        <div>
          <button onClick={requestPasswordReset} className="bg-yellow-500 text-white px-4 py-2 rounded mr-2">修改密碼</button>
          <button onClick={handleLogout} className="bg-red-500 text-white px-4 py-2 rounded">登出</button>
        </div>
      </div>

      <div className="bg-white p-4 rounded shadow mb-6 flex gap-4 items-center">
        <input type="file" accept=".xlsx, .xls" onChange={(e) => setFile(e.target.files[0])} className="border p-1" />
        <button onClick={handleImport} className="bg-green-600 text-white px-4 py-2 rounded">匯入 Excel 成績</button>
        <button onClick={handleExport} className="bg-blue-600 text-white px-4 py-2 rounded ml-auto">匯出 Excel 成績</button>
      </div>

{/* 編輯表單區塊 */}
      {editingStudent && (
        <form onSubmit={handleUpdate} className="bg-blue-50 p-4 rounded shadow mb-6 border border-blue-200">
          <h3 className="font-bold mb-4 text-lg border-b pb-2">編輯學生資料與成績</h3>
          
	  {/* 基本資料修改 */}
          <div className="flex gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">學號</label>
              <input 
                type="text" required
                className="w-24 p-1 border rounded focus:outline-none focus:ring-2 focus:ring-blue-400"
                value={editingStudent.student_id || ''}
                onChange={e => setEditingStudent({...editingStudent, student_id: e.target.value})}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">姓名</label>
              <input 
                type="text" required
                className="w-32 p-1 border rounded focus:outline-none focus:ring-2 focus:ring-blue-400"
                value={editingStudent.name}
                onChange={e => setEditingStudent({...editingStudent, name: e.target.value})}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email帳號</label>
              <input 
                type="email" required
                className="w-64 p-1 border rounded focus:outline-none focus:ring-2 focus:ring-blue-400"
                value={editingStudent.email}
                onChange={e => setEditingStudent({...editingStudent, email: e.target.value})}
              />
            </div>
          </div>

          {/* 成績修改 */}
          <div className="flex gap-2 mb-4">
            {[
              { key: 'chinese', name: '國文' },
              { key: 'english', name: '英文' },
              { key: 'math', name: '數學' },
              { key: 'physics', name: '物理' },
              { key: 'chemistry', name: '化學' }
            ].map(sub => (
              <div key={sub.key}>
                <label className="block text-sm font-medium text-gray-700 mb-1">{sub.name}</label>
                <input 
                  type="number" step="0.1"
                  className="w-20 p-1 border rounded focus:outline-none focus:ring-2 focus:ring-blue-400"
                  value={editingStudent.grades[sub.key]}
                  onChange={e => setEditingStudent({
                    ...editingStudent, 
                    grades: {...editingStudent.grades, [sub.key]: parseFloat(e.target.value) || 0}
                  })}
                />
              </div>
            ))}
          </div>

          <button type="submit" className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-1 rounded mr-2 transition">儲存修改</button>
          <button type="button" onClick={() => setEditingStudent(null)} className="bg-gray-400 hover:bg-gray-500 text-white px-4 py-1 rounded transition">取消</button>
        </form>
      )}

{/* 學生列表 */}
      <div className="bg-white rounded shadow overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-800 text-white">
              <th className="p-3">學號</th>   {/* 分開獨立 */}
              <th className="p-3">Email</th> {/* 分開獨立 */}
              <th className="p-3">姓名</th>
              <th className="p-3">國文</th>
              <th className="p-3">英文</th>
              <th className="p-3">數學</th>
              <th className="p-3">物理</th>
              <th className="p-3">化學</th>
              <th className="p-3">操作</th>
            </tr>
          </thead>
          <tbody>
            {students.map(s => (
              <tr key={s.id} className="border-b hover:bg-gray-50">
                <td className="p-3 font-mono text-blue-600 font-bold">{s.student_id}</td>
                {/* 套用 Email 隱碼 */}
                <td className="p-3">{maskEmail(s.email)}</td>
                {/* 套用 姓名隱碼 */}
                <td className="p-3 font-bold">{maskName(s.name)}</td>
                <td className="p-3">{s.grades.chinese}</td>
                <td className="p-3">{s.grades.english}</td>
                <td className="p-3">{s.grades.math}</td>
                <td className="p-3">{s.grades.physics}</td>
                <td className="p-3">{s.grades.chemistry}</td>
                <td className="p-3">
                  {/* 當老師點擊編輯時，傳入的是含有「真實資料」的物件 s */}
                  <button onClick={() => setEditingStudent(s)} className="text-blue-600 hover:underline font-medium">編輯資料</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default TeacherDashboard;