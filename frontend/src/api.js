import axios from 'axios';

const api = axios.create({
  baseURL: 'http://127.0.0.1:5000', // 後端網址，將原本的 http://127.0.0.1:5000 替換成 Render 的網址，其他使用者請自行修改
});

// 在發送請求前，自動加上 Token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

export default api;