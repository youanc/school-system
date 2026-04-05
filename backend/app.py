import os
from dotenv import load_dotenv # 讀取環境變數
# 載入 .env 檔案中的變數
load_dotenv()

import re
import datetime
import io
import pandas as pd
from flask import Flask, request, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from sqlalchemy import inspect
# 注意這裡多引入了 get_jwt 來取得額外資訊
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, get_jwt
from flask_mail import Mail, Message
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ================= 設定區 =================
BASE_DIR = os.path.abspath(os.path.dirname(__name__))

# 優先讀取環境變數的 DATABASE_URL，如果沒設定，才退回使用本地的 sqlite
database_url = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///' + os.path.join(BASE_DIR, 'school.db')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# JWT 設定 (30 分鐘無動作過期)
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', '預設的備用安全碼')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(minutes=30)

# Email 設定 (請替換為你的真實設定，建議使用 Gmail 應用程式密碼)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)
mail = Mail(app)

# ================= 資料庫模型 =================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # 加入學號欄位，設定 unique=True，nullable=True 是因為老師沒有學號
    student_id = db.Column(db.String(20), unique=True, nullable=True) 
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=True)
    role = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    is_verified = db.Column(db.Boolean, default=False)
    grade = db.relationship('Grade', backref='student', uselist=False, cascade="all, delete-orphan")

class Grade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    chinese = db.Column(db.Float, default=0)
    english = db.Column(db.Float, default=0)
    math = db.Column(db.Float, default=0)
    physics = db.Column(db.Float, default=0)
    chemistry = db.Column(db.Float, default=0)

# ================= 輔助函數 =================
def is_strong_password(password):
    return re.match(r'^(?=.*[a-zA-Z])(?=.*\d)(?=.*[\W_]).{8,}$', password)

def mask_name(name):
    if not name: return ""
    if len(name) <= 2:
        return name[0] + "O"
    return name[0] + "O" * (len(name) - 2) + name[-1]

def send_reset_email(user_email):
    # 修正：identity 必須是字串，附加資訊放入 additional_claims
    reset_token = create_access_token(
        identity=user_email, 
        additional_claims={'action': 'reset_password'}, 
        expires_delta=datetime.timedelta(hours=1)
    )
    msg = Message("系統登入與密碼設定通知", sender=app.config['MAIL_USERNAME'], recipients=[user_email])
    reset_link = f"http://localhost:5173/set-password?token={reset_token}"
    msg.body = f"請點擊以下連結設定您的密碼 (連結有效時間為 1 小時):\n\n{reset_link}"
    try:
        mail.send(msg)
        return True
    except Exception as e:
        print(f"寄信失敗: {e}")
        return False

# ================= 認證路由 =================
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"msg": "帳號不存在"}), 404
        
    if not user.is_verified:
        success = send_reset_email(user.email)
        if success:
            return jsonify({"msg": "此帳號尚未驗證，已發送設定密碼信件至您的 Email，請前往收信"}), 403
        else:
            return jsonify({"msg": "寄發驗證信失敗，請聯絡管理員"}), 500

    if user and bcrypt.check_password_hash(user.password_hash, password):
        # 修正：identity 必須是字串，附加資訊放入 additional_claims
        access_token = create_access_token(
            identity=user.email, 
            additional_claims={'role': user.role}
        )
        return jsonify(access_token=access_token, role=user.role, name=user.name), 200
    
    return jsonify({"msg": "密碼錯誤"}), 401

@app.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    email = data.get('email')
    user = User.query.filter_by(email=email).first()
    if user:
        send_reset_email(user.email)
    return jsonify({"msg": "若該信箱存在，系統已發送密碼重設信"}), 200

@app.route('/set-password', methods=['POST'])
@jwt_required()
def set_password():
    email = get_jwt_identity() # 取得字串 identity
    claims = get_jwt()         # 取得附加資訊

    if claims.get('action') != 'reset_password':
        return jsonify({"msg": "無效的 Token 類型"}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"msg": "找不到該使用者"}), 404

    new_password = request.json.get('password')
    if not is_strong_password(new_password):
        return jsonify({"msg": "密碼必須包含英數字與特殊符號，且至少8碼"}), 400
        
    user.password_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
    user.is_verified = True
    db.session.commit()
    return jsonify({"msg": "密碼設定成功，請重新登入"}), 200

# ================= 學生專屬路由 =================
@app.route('/student/grades', methods=['GET'])
@jwt_required()
def get_student_grades():
    email = get_jwt_identity()
    claims = get_jwt()
    if claims.get('role') != 'student':
        return jsonify({"msg": "權限不足"}), 403
        
    user = User.query.filter_by(email=email).first()
    grade = Grade.query.filter_by(student_id=user.id).first()
    
    grades_data = {
        "國文": grade.chinese, "英文": grade.english, "數學": grade.math, 
        "物理": grade.physics, "化學": grade.chemistry
    } if grade else None

    return jsonify({
	"student_id": user.student_id,
        "email": user.email,
        "name": mask_name(user.name),
        "grades": grades_data
    }), 200

# ================= 老師專屬路由 =================
@app.route('/teacher/students', methods=['GET'])
@jwt_required()
def get_all_students():
    claims = get_jwt()
    if claims.get('role') != 'teacher':
        return jsonify({"msg": "權限不足"}), 403

    students = User.query.filter_by(role='student').all()
    result = []
    for s in students:
        g = s.grade
        result.append({
            "id": s.id,
            "student_id": s.student_id,
            "email": s.email,
            "name": s.name, 
            "is_verified": s.is_verified,
            "grades": {
                "chinese": g.chinese if g else 0,
                "english": g.english if g else 0,
                "math": g.math if g else 0,
                "physics": g.physics if g else 0,
                "chemistry": g.chemistry if g else 0,
            }
        })
    return jsonify(result), 200

@app.route('/teacher/students', methods=['POST'])
@jwt_required()
def add_student():
    claims = get_jwt()
    if claims.get('role') != 'teacher':
        return jsonify({"msg": "權限不足"}), 403

    data = request.get_json()
    if User.query.filter_by(email=data['email']).first():
        return jsonify({"msg": "Email 已存在"}), 400

    new_student = User(email=data['email'], name=data['name'], role='student', is_verified=False)
    db.session.add(new_student)
    db.session.flush()

    new_grade = Grade(student_id=new_student.id, **data.get('grades', {}))
    db.session.add(new_grade)
    db.session.commit()
    
    return jsonify({"msg": "學生新增成功"}), 201

@app.route('/teacher/students/<int:id>', methods=['PUT'])
@jwt_required()
def update_student(id):
    claims = get_jwt()
    if claims.get('role') != 'teacher':
        return jsonify({"msg": "權限不足"}), 403

    data = request.get_json()
    student = User.query.get_or_404(id)
    
    # 檢查並更新學號
    if 'student_id' in data and data['student_id'] != student.student_id:
        if User.query.filter_by(student_id=data['student_id']).first():
            return jsonify({"msg": "更新失敗：此學號已存在！"}), 400
        student.student_id = data['student_id']

    # 檢查並更新 Email
    if 'email' in data and data['email'] != student.email:
        if User.query.filter_by(email=data['email']).first():
            return jsonify({"msg": "更新失敗：此 Email 已經被使用！"}), 400
        student.email = data['email']

    # 更新姓名
    if 'name' in data:
        student.name = data['name']
        
    # 更新成績
    if 'grades' in data:
        grade = student.grade
        if not grade:
            grade = Grade(student_id=student.id)
            db.session.add(grade)
        grade.chinese = data['grades'].get('chinese', grade.chinese)
        grade.english = data['grades'].get('english', grade.english)
        grade.math = data['grades'].get('math', grade.math)
        grade.physics = data['grades'].get('physics', grade.physics)
        grade.chemistry = data['grades'].get('chemistry', grade.chemistry)

    db.session.commit()
    return jsonify({"msg": "學生資料與成績更新成功"}), 200

@app.route('/teacher/students/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_student(id):
    claims = get_jwt()
    if claims.get('role') != 'teacher':
        return jsonify({"msg": "權限不足"}), 403

    student = User.query.get_or_404(id)
    db.session.delete(student)
    db.session.commit()
    return jsonify({"msg": "學生刪除成功"}), 200

@app.route('/teacher/import-grades', methods=['POST'])
@jwt_required()
def import_grades():
    claims = get_jwt()
    if claims.get('role') != 'teacher':
        return jsonify({"msg": "權限不足"}), 403
        
    if 'file' not in request.files:
        return jsonify({"msg": "請上傳檔案"}), 400
        
    file = request.files['file']
    try:
        df = pd.read_excel(file)
        
        for _, row in df.iterrows():
            # 取得 Excel 裡的學號，轉成字串並去除空白
            student_id_val = str(row.get('學號', '')).strip()
            
            # Pandas 讀取 Excel 數字時有時會變成浮點數 (例如 '001' 變 '1.0')
            # 這裡做一個簡單的安全處理，去除小數點零
            if student_id_val.endswith('.0'):
                student_id_val = student_id_val[:-2]
            
            # 若因 Excel 格式設定問題，把 '001' 讀成 '1'，可自動補齊三碼 (視你的學號規則而定)
            if len(student_id_val) < 3 and student_id_val.isdigit():
                student_id_val = student_id_val.zfill(3)

            # 以「學號」作為 Key 尋找學生
            student = User.query.filter_by(student_id=student_id_val, role='student').first()
            
            if student:
                grade = student.grade
                if not grade:
                    grade = Grade(student_id=student.id)
                    db.session.add(grade)
                
                # 寫入成績，並使用 pd.notna 確保格子不是空的 (NaN)
                if pd.notna(row.get('國文')): grade.chinese = float(row.get('國文'))
                if pd.notna(row.get('英文')): grade.english = float(row.get('英文'))
                if pd.notna(row.get('數學')): grade.math = float(row.get('數學'))
                if pd.notna(row.get('物理')): grade.physics = float(row.get('物理'))
                if pd.notna(row.get('化學')): grade.chemistry = float(row.get('化學'))
                
        db.session.commit()
        return jsonify({"msg": "成績匯入成功"}), 200
    except Exception as e:
        return jsonify({"msg": f"匯入失敗: {str(e)}"}), 500

@app.route('/teacher/export-grades', methods=['GET'])
@jwt_required()
def export_grades():
    claims = get_jwt()
    if claims.get('role') != 'teacher':
        return jsonify({"msg": "權限不足"}), 403

    students = User.query.filter_by(role='student').all()
    data = []
    for s in students:
        g = s.grade

        data.append({
            "學號": s.student_id,
            "Email": s.email,
            "姓名": s.name,
            "國文": g.chinese if g else 0,
            "英文": g.english if g else 0,
            "數學": g.math if g else 0,
            "物理": g.physics if g else 0,
            "化學": g.chemistry if g else 0,
        })
    
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='學生成績單')
    
    output.seek(0)
    return send_file(
        output,
        download_name='students_grades.xlsx',
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

# ================= 系統初始化 =================
def init_db():
    with app.app_context():
        inspector = inspect(db.engine)
        if not inspector.has_table("user"):
            print("偵測到全新的資料庫，開始建立資料表與初始資料...")
            db.create_all()
            
            teacher = User(email=app.config['MAIL_USERNAME'], role='teacher', name='Admin Teacher', is_verified=False)
            db.session.add(teacher)
            
            for i in range(1, 51):
                s_id = f'{i:03d}' # 產生 001, 002...
                student_email = f'{s_id}@abc.edu.tw'
                # 這裡把 student_id=s_id 存進去
                student = User(student_id=s_id, email=student_email, role='student', name=f'學生{i}號', is_verified=False)
                db.session.add(student)
                db.session.flush()
                grade = Grade(student_id=student.id)
                db.session.add(grade)

            db.session.commit()
            print("資料庫初始化完成：已建立老師與 001~050 學生帳號。")
        else:
            print("資料庫與資料表已存在，略過初始化。")

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)