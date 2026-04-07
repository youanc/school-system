import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import Swal from 'sweetalert2';

const TeacherDashboard = () => {
  const [exams, setExams] = useState([]);
  const [selectedExamId, setSelectedExamId] = useState('');
  const [students, setStudents] = useState([]);
  const [file, setFile] = useState(null);
  const [editingStudent, setEditingStudent] = useState(null);

  // 新增狀態：頁籤控制與全體學生
  const [activeTab, setActiveTab] = useState('exams'); 
  const [allStudents, setAllStudents] = useState([]);

  const navigate = useNavigate();
  const currentExam = exams.find(e => e.id == selectedExamId);

  const maskName = (name) => {
    if (!name) return "";
    if (name.length <= 2) return name[0] + "O";
    return name[0] + "O".repeat(name.length - 2) + name[name.length - 1];
  };

  const maskEmail = (email) => {
    if (!email) return "";
    const [local, domain] = email.split('@');
    if (!domain) return email;
    if (local.length <= 2) return local[0] + "***@" + domain;
    return local.substring(0, 2) + "****@" + domain;
  };

  const fetchExams = async () => {
    const res = await api.get('/exams');
    setExams(res.data);
    if (res.data.length > 0 && !res.data.find(e => e.id == selectedExamId)) {
      setSelectedExamId(res.data[0].id);
    } else if (res.data.length === 0) {
      setSelectedExamId('');
      setStudents([]);
    }
  };

  const fetchStudents = async () => {
    if (!selectedExamId) return;
    try {
      const res = await api.get(`/teacher/students/${selectedExamId}`);
      setStudents(res.data);
    } catch (err) {
      Swal.fire('錯誤', '連線異常，請重新登入', 'error');
      navigate('/login');
    }
  };

  const fetchAllStudents = async () => {
    try {
      const res = await api.get('/teacher/all-students');
      setAllStudents(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => { fetchExams(); }, []);
  useEffect(() => { fetchStudents(); }, [selectedExamId]);
  
  // 當切換到「學生管理」時才去抓取全體學生資料
  useEffect(() => {
    if (activeTab === 'students') {
      fetchAllStudents();
    }
  }, [activeTab]);

  const handleLogout = () => { localStorage.removeItem('token'); navigate('/login'); };

  const requestPasswordReset = async () => {
    let email = localStorage.getItem('userEmail');
    if (!email) {
      const { value: inputEmail } = await Swal.fire({
        title: '請輸入您的教師 Email',
        input: 'email',
        inputPlaceholder: '範例: teacher@school.edu.tw',
        showCancelButton: true,
        confirmButtonText: '發送重置信',
        cancelButtonText: '取消'
      });
      if (!inputEmail) return;
      email = inputEmail;
    }

    try {
      await api.post('/forgot-password', { email });
      localStorage.setItem('emailCooldownTime', Date.now().toString());
      Swal.fire('發送成功', '密碼重置連結已發送至信箱。', 'success');
    } catch (error) {
      Swal.fire('發送失敗', error.response?.data?.msg || "發生錯誤，請稍後再試", 'error');
    }
  };

  // =============== 【已修復】合併錯誤的語法 ===============
  const handleImport = async () => {
    if (!file) return Swal.fire('提示', '請先選擇 Excel 檔案', 'warning');
    const result = await Swal.fire({
      title: '確定要匯入資料嗎？',
      text: "注意：若檔案包含「學生名單」，系統將以該名單為主，未在 Excel 上的舊學生及其成績將被【永久移除】！",
      icon: 'warning',
      showCancelButton: true,
      confirmButtonColor: '#3085d6',
      cancelButtonColor: '#d33',
      confirmButtonText: '確定匯入並覆蓋',
      cancelButtonText: '取消'
    });

    if (result.isConfirmed) {
      const formData = new FormData(); 
      formData.append('file', file);
      try {
        const response = await api.post('/teacher/import-grades', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
        Swal.fire('成功', response.data.msg, 'success');
        setFile(null);
        document.querySelector('input[type="file"]').value = '';
        await fetchExams();
        await fetchStudents();
      } catch (err) {
        Swal.fire('匯入失敗', err.response?.data?.msg || '發生未知錯誤', 'error');
      }
    }
  };
  // =========================================================

  const handleExport = async () => {
    try {
      const res = await api.get('/teacher/export-grades', { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url; 
      link.setAttribute('download', 'school_data_export.xlsx'); 
      document.body.appendChild(link); 
      link.click();
    } catch (err) { Swal.fire('錯誤', '匯出失敗', 'error'); }
  };

  const handleUpdate = async (e) => {
    e.preventDefault();
    try {
      await api.put(`/teacher/students/${editingStudent.id}/${selectedExamId}`, editingStudent);
      Swal.fire({ title: '更新成功', icon: 'success', timer: 1500, showConfirmButton: false });
      setEditingStudent(null);
      fetchStudents();
    } catch (err) {
      Swal.fire('錯誤', err.response?.data?.msg || '更新失敗', 'error');
    }
  };

  const handleRenameExam = async () => {
    const { value: newName } = await Swal.fire({
      title: '重新命名考試',
      input: 'text',
      inputValue: currentExam.name,
      showCancelButton: true,
      inputValidator: (value) => { if (!value) return '名稱不能為空！' }
    });

    if (newName && newName !== currentExam.name) {
      try {
        await api.put(`/teacher/exams/${selectedExamId}`, { name: newName });
        Swal.fire('成功', '考試名稱已變更', 'success');
        fetchExams();
      } catch (err) { Swal.fire('錯誤', err.response?.data?.msg, 'error'); }
    }
  };

  const handleToggleLock = async () => {
    const isLocked = currentExam.is_locked;
    const actionText = isLocked ? '解除鎖定' : '鎖定';
    const result = await Swal.fire({
      title: `確定要${actionText}此考試嗎？`,
      text: isLocked ? "解鎖後可以重新編輯或匯入成績。" : "鎖定後，此考試成績將無法修改或刪除。",
      icon: 'question',
      showCancelButton: true,
      confirmButtonText: `確定${actionText}`
    });

    if (result.isConfirmed) {
      try {
        await api.put(`/teacher/exams/${selectedExamId}`, { is_locked: !isLocked });
        Swal.fire('成功', `已${actionText}`, 'success');
        fetchExams();
      } catch (err) { Swal.fire('錯誤', '操作失敗', 'error'); }
    }
  };

  const handleDeleteExam = async () => {
    if (currentExam.is_locked) return Swal.fire('提示', '已鎖定的考試無法刪除。', 'warning');
    const result = await Swal.fire({
      title: '警告',
      text: `確定要刪除「${currentExam.name}」嗎？此操作無法復原！`,
      icon: 'error',
      showCancelButton: true,
      confirmButtonColor: '#d33',
      confirmButtonText: '確定刪除'
    });

    if (result.isConfirmed) {
      try {
        await api.delete(`/teacher/exams/${selectedExamId}`);
        Swal.fire('已刪除', '考試成績已清空', 'success');
        fetchExams();
      } catch (err) { Swal.fire('錯誤', err.response?.data?.msg, 'error'); }
    }
  };

  const handleAddStudent = async () => {
    const { value: formValues } = await Swal.fire({
      title: '新增學生',
      html:
        '<input id="swal-id" class="swal2-input" placeholder="學號 (如: 001)">' +
        '<input id="swal-name" class="swal2-input" placeholder="姓名">' +
        '<input id="swal-email" type="email" class="swal2-input" placeholder="Email">',
      focusConfirm: false,
      showCancelButton: true,
      confirmButtonText: '新增',
      cancelButtonText: '取消',
      preConfirm: () => {
        const id = document.getElementById('swal-id').value;
        const name = document.getElementById('swal-name').value;
        const email = document.getElementById('swal-email').value;
        if (!id || !name || !email) {
          Swal.showValidationMessage('請完整填寫所有欄位');
          return false;
        }
        return { student_id: id, name, email };
      }
    });

    if (formValues) {
      try {
        const res = await api.post('/teacher/student', formValues);
        Swal.fire('成功', res.data.msg, 'success');
        fetchAllStudents();
      } catch (err) {
        Swal.fire('新增失敗', err.response?.data?.msg || '發生錯誤', 'error');
      }
    }
  };

  const handleDeleteStudent = async (id, name) => {
    const result = await Swal.fire({
      title: `確定要刪除 ${name} 嗎？`,
      text: "此動作會連同刪除該學生的未鎖定成績紀錄，且無法復原！",
      icon: 'warning',
      showCancelButton: true,
      confirmButtonColor: '#d33',
      confirmButtonText: '確定刪除'
    });

    if (result.isConfirmed) {
      try {
        const res = await api.delete(`/teacher/student/${id}`);
        Swal.fire('已刪除', res.data.msg, 'success');
        fetchAllStudents();
        if (selectedExamId) fetchStudents();
      } catch (err) {
        Swal.fire('刪除失敗', err.response?.data?.msg || '發生錯誤', 'error');
      }
    }
  };

  const allSubjects = Array.from(new Set(students.flatMap(s => Object.keys(s.grades || {}))));

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-6 bg-white p-4 rounded shadow">
        <h1 className="text-2xl font-bold">教師管理後台</h1>
        <div>
          <button onClick={requestPasswordReset} className="bg-yellow-500 text-white px-4 py-2 rounded mr-2 hover:bg-yellow-600 transition">修改密碼</button>
          <button onClick={handleLogout} className="bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600 transition">登出</button>
        </div>
      </div>

      <div className="flex gap-2 mb-6 border-b-2 border-gray-200 pb-2">
        <button 
          onClick={() => setActiveTab('exams')}
          className={`px-6 py-2 rounded-t-lg font-bold transition ${activeTab === 'exams' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-600 hover:bg-gray-300'}`}
        >
          成績與考試管理
        </button>
        <button 
          onClick={() => setActiveTab('students')}
          className={`px-6 py-2 rounded-t-lg font-bold transition ${activeTab === 'students' ? 'bg-purple-600 text-white' : 'bg-gray-200 text-gray-600 hover:bg-gray-300'}`}
        >
          學生名單總覽
        </button>
      </div>

      {activeTab === 'exams' && (
        <div className="animate-fade-in">
          <div className="bg-white p-4 rounded shadow mb-6 flex gap-4 items-center border-l-4 border-green-500">
            <input type="file" accept=".xlsx, .xls" onChange={(e) => setFile(e.target.files[0])} className="border p-1" />
            <button onClick={handleImport} className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 transition">匯入多筆 Excel</button>
            <button onClick={handleExport} className="bg-blue-600 text-white px-4 py-2 rounded ml-auto hover:bg-blue-700 transition">匯出所有考試 Excel</button>
          </div>

          <div className="mb-6 flex flex-wrap items-center gap-4 bg-white p-4 rounded shadow border-l-4 border-purple-500">
            <label className="font-bold text-gray-700">選擇考試場次：</label>
            <select 
              className="border p-2 rounded w-64 focus:ring-2 focus:ring-purple-400 bg-gray-50"
              value={selectedExamId} 
              onChange={(e) => {
                setSelectedExamId(e.target.value);
                setEditingStudent(null);
              }}
            >
              {exams.map(exam => <option key={exam.id} value={exam.id}>{exam.name} {exam.is_locked ? '(🔒 已鎖定)' : ''}</option>)}
            </select>
            
            {currentExam && (
              <div className="flex gap-2 ml-auto">
                <button onClick={handleRenameExam} className="bg-gray-200 text-gray-700 px-3 py-1 rounded hover:bg-gray-300">重新命名</button>
                <button onClick={handleToggleLock} className={`${currentExam.is_locked ? 'bg-yellow-500 hover:bg-yellow-600' : 'bg-gray-600 hover:bg-gray-700'} text-white px-3 py-1 rounded`}>
                  {currentExam.is_locked ? '🔓 解除鎖定' : '🔒 鎖定成績'}
                </button>
                <button onClick={handleDeleteExam} className="bg-red-100 text-red-600 px-3 py-1 rounded hover:bg-red-200">刪除此考試</button>
              </div>
            )}
          </div>

          {editingStudent && currentExam && !currentExam.is_locked && (
            <form onSubmit={handleUpdate} className="bg-blue-50 p-4 rounded shadow mb-6 border border-blue-200">
              <h3 className="font-bold mb-4 text-lg border-b pb-2 text-blue-800">編輯學生資料 - {currentExam.name}</h3>
              <div className="flex gap-4 mb-4">
                <div><label className="block text-sm">學號</label><input type="text" className="w-24 p-1 border rounded" value={editingStudent.student_id || ''} onChange={e => setEditingStudent({...editingStudent, student_id: e.target.value})} /></div>
                <div><label className="block text-sm">姓名</label><input type="text" className="w-32 p-1 border rounded" value={editingStudent.name} onChange={e => setEditingStudent({...editingStudent, name: e.target.value})} /></div>
                <div><label className="block text-sm">Email</label><input type="email" className="w-64 p-1 border rounded" value={editingStudent.email} onChange={e => setEditingStudent({...editingStudent, email: e.target.value})} /></div>
              </div>
              <div className="flex gap-2 mb-4 flex-wrap">
                {allSubjects.map(sub => (
                  <div key={sub}>
                    <label className="block text-sm font-medium text-gray-700 mb-1">{sub}</label>
                    <input 
                      type="number" step="0.1" className="w-20 p-1 border rounded"
                      value={editingStudent.grades[sub] || ''}
                      onChange={e => setEditingStudent({ ...editingStudent, grades: {...editingStudent.grades, [sub]: parseFloat(e.target.value) || 0} })}
                    />
                  </div>
                ))}
              </div>
              <button type="submit" className="bg-blue-500 text-white px-4 py-1 rounded mr-2 hover:bg-blue-600">儲存</button>
              <button type="button" onClick={() => setEditingStudent(null)} className="bg-gray-400 text-white px-4 py-1 rounded hover:bg-gray-500">取消</button>
            </form>
          )}

          <div className="bg-white rounded shadow overflow-x-auto">
            <table className="w-full text-left border-collapse whitespace-nowrap">
              <thead>
                <tr className="bg-gray-800 text-white">
                  <th className="p-3">學號</th>
                  <th className="p-3">Email</th>
                  <th className="p-3">姓名</th>
                  {allSubjects.map(sub => <th key={sub} className="p-3">{sub}</th>)}
                  <th className="p-3">操作</th>
                </tr>
              </thead>
              <tbody>
                {students.map(s => (
                  <tr key={s.id} className={`border-b ${currentExam?.is_locked ? 'bg-gray-50' : 'hover:bg-blue-50'}`}>
                    <td className="p-3 font-mono text-blue-600 font-bold">{s.student_id}</td>
                    <td className="p-3 text-gray-600">{maskEmail(s.email)}</td>
                    <td className="p-3 font-bold">{maskName(s.name)}</td>
                    {allSubjects.map(sub => (
                      <td key={sub} className="p-3">{s.grades[sub] ?? '-'}</td>
                    ))}
                    <td className="p-3">
                      {currentExam?.is_locked ? (
                        <span className="text-gray-400 text-sm cursor-not-allowed">🔒 唯讀</span>
                      ) : (
                        <button onClick={() => setEditingStudent(s)} className="text-blue-600 hover:text-blue-800 font-medium">✏️ 編輯</button>
                      )}
                    </td>
                  </tr>
                ))}
                {students.length === 0 && (
                  <tr><td colSpan="10" className="p-6 text-center text-gray-500">目前無成績資料，請匯入 Excel</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'students' && (
        <div className="animate-fade-in">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-bold text-gray-700">全校學生名單 ({allStudents.length} 人)</h2>
            <button onClick={handleAddStudent} className="bg-purple-600 text-white px-4 py-2 rounded shadow hover:bg-purple-700 transition">
              + 新增學生
            </button>
          </div>

          <div className="bg-white rounded shadow overflow-hidden">
            <table className="w-full text-left border-collapse whitespace-nowrap">
              <thead>
                <tr className="bg-gray-800 text-white">
                  <th className="p-3">學號</th>
                  <th className="p-3">姓名</th>
                  <th className="p-3">Email</th>
                  <th className="p-3">帳號狀態</th>
                  <th className="p-3">操作</th>
                </tr>
              </thead>
              <tbody>
                {allStudents.map(s => (
                  <tr key={s.id} className="border-b hover:bg-purple-50 transition">
                    <td className="p-3 font-mono font-bold text-purple-700">{s.student_id}</td>
                    <td className="p-3 font-bold">{maskName(s.name)}</td>
                    <td className="p-3 text-gray-600">{maskEmail(s.email)}</td>
                    <td className="p-3">
                      {s.is_verified ? 
                        <span className="bg-green-100 text-green-700 px-2 py-1 rounded text-sm">已啟用</span> : 
                        <span className="bg-yellow-100 text-yellow-700 px-2 py-1 rounded text-sm">尚未設定密碼</span>
                      }
                    </td>
                    <td className="p-3">
                      <button onClick={() => handleDeleteStudent(s.id, s.name)} className="text-red-500 hover:text-red-700 font-medium">
                        刪除
                      </button>
                    </td>
                  </tr>
                ))}
                {allStudents.length === 0 && (
                  <tr><td colSpan="5" className="p-6 text-center text-gray-500">目前系統中沒有任何學生</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default TeacherDashboard;