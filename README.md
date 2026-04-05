# 校園成績管理系統 (School Grade Management System)



這是一個基於**前後端分離**架構開發的校園成績管理系統。具備完整的角色權限控制（教師/學生）、安全的密碼機制（JWT + Bcrypt 加密）、以及便利的 Excel 匯入/匯出功能。



## 🌟 系統特色



* **角色權限分離**：教師可管理所有學生成績與基本資料，學生僅能查詢自己的成績。

* **安全認證機制**：使用 JWT (JSON Web Token) 進行登入驗證，並具備 30 分鐘閒置自動登出功能。

* **首次登入 / 忘記密碼**：串接 Gmail SMTP 寄送含有時效性 Token 的密碼設定連結。

* **批次資料處理**：教師可透過 Excel 檔 (`.xlsx`) 快速匯入或匯出全班成績。

* **隱私保護**：列表資料實作姓名與 Email 隱碼機制。



## 🛠️ 技術棧 (Tech Stack)



* **前端 (Frontend)**: React, Vite, Tailwind CSS, Axios, React Router

* **後端 (Backend)**: Python, Flask, Flask-SQLAlchemy, Flask-JWT-Extended, Pandas

* **資料庫 (Database)**: SQLite



---



## 🚀 快速開始 (Getting Started)



請依照以下步驟，在你的本地電腦上啟動此專案。



### 1. 環境要求 (Prerequisites)

在開始之前，請確保你的電腦已經安裝了以下軟體：

* [Node.js](https://nodejs.org/) (建議安裝 LTS 版本，用於執行前端。**安裝 Node.js 時會自動包含 npm 套件管理工具**)

* [Python](https://www.python.org/downloads/) (建議安裝 3.9 以上版本，用於執行後端)



### 2. 下載專案 (Clone the repository)

打開終端機 (Terminal / 命命提示字元)，將專案下載到你的電腦中：

```bash

git clone https://github.com/happyfamily20190307/school-system.git

cd school-system

```

---



### 3. 後端設定與啟動 (Backend Setup)


**步驟 3-1：建立虛擬環境並安裝套件**
為了避免與系統其他專案的套件版本衝突，強烈建議建立並使用虛擬環境 (Virtual Environment)。

```bash
cd backend

# 1. 建立虛擬環境 (名稱為 venv)
python -m venv venv

# 2. 啟動虛擬環境
# Windows 系統請輸入：
venv\Scripts\activate
# macOS/Linux 系統請輸入：
# source venv/bin/activate

# 3. 安裝系統所需的相依套件 (透過 requirements.txt 一鍵安裝)
pip install -r requirements.txt

```



**步驟 3-2：建立環境變數檔 (.env)**

為了保護密碼安全，本專案沒有將機密上傳至 GitHub。請在 `backend` 資料夾下，手動新增一個名為 `.env` 的純文字檔，並填入以下內容：

```env

# 請將下方內容替換為你真實的 Gmail 帳號與應用程式密碼

MAIL_USERNAME=your_email@gmail.com

MAIL_PASSWORD=your_app_password

JWT_SECRET_KEY=your_super_secret_jwt_key_here

MAIL_PASSWORD 請使用「應用程式密碼」(App Password)，否則可能會出現 535 5.7.8 BadCredentials 錯誤
這是目前最標準的做法。如果你啟用了兩步驟驗證（2FA），你不能使用平常登入 Gmail 的密碼。
1. 前往你的 Google 帳號設定。(https://myaccount.google.com/)
2. 點擊左側的 安全性。
3. 確認你已開啟 「兩步驟驗證」。
4. 在搜尋欄搜尋 「應用程式密碼」 (App Passwords)。
5. 建立一個新的名稱（例如：Python Mail App），Google 會產生一組 16 位元的序號。
6. 將這組 16 位元序號替換掉你程式碼中原本的密碼（不含空格）。
```



**步驟 3-3：啟動 Flask 伺服器**

```bash

python app.py

```

> **💡 提示：** 首次啟動時，系統會自動建立 `school.db` 資料庫，並生成 1 位預設教師 (你在 .env 設定的信箱) 與 50 位預設學生 (`001@abc.edu.tw` ~ `050@abc.edu.tw`)。

> 伺服器啟動後，請保持這個終端機視窗開啟。



---



### 4. 前端設定與啟動 (Frontend Setup)



請**打開一個全新的終端機視窗**（原本跑後端的那個不要關掉），確保路徑在專案主資料夾下，然後執行：



**步驟 4-1：進入前端資料夾並安裝相依套件**

```bash

cd frontend

npm install

```



**步驟 4-2：啟動 React 開發伺服器**

```bash

npm run dev

```

啟動成功後，終端機會顯示一個本地網址（通常是 `http://localhost:5173`），請在瀏覽器中開啟該網址。



---



## 📖 系統操作指南 (How to Use)



\### 首次登入測試

1.  開啟前端網頁 (`http://localhost:5173`)。

2.  輸入教師預設帳號：(你在 .env 設定的信箱)。

3.  **密碼欄位請留空**，直接點擊「登入」。

4.  系統會提示權限不足，並自動寄發一封「設定密碼信件」到你在 `.env` 設定的信箱。

5.  前往你的 Email 收信，點擊信中的設定連結（請確認網址的 port 與你前端運行的 port 一致）。

6.  設定符合安全規範的密碼（至少8碼，需包含英數字與特殊符號）。

7.  設定完成後，即可使用新密碼登入教師管理後台！



### 預設帳號清單

* **教師帳號**: (你在 .env 設定的信箱)

* **學生帳號**: `001@abc.edu.tw` ~ `050@abc.edu.tw` (共 50 組)

```

