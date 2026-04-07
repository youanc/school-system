import os
from dotenv import load_dotenv
load_dotenv()

import re
import datetime
import io
import pandas as pd
from flask import Flask, request, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from sqlalchemy import inspect
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, get_jwt
from flask_mail import Mail, Message
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.abspath(os.path.dirname(__name__))
database_url = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///' + os.path.join(BASE_DIR, 'school.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', '預設的備用安全碼')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(minutes=30)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)
mail = Mail(app)

from sqlalchemy import event
from sqlalchemy.engine import Engine

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
# ================= 資料庫模型 =================
class User(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	student_id = db.Column(db.String(20), unique=True, nullable=True) 
	email = db.Column(db.String(120), unique=True, nullable=False)
	password_hash = db.Column(db.String(128), nullable=True)
	role = db.Column(db.String(20), nullable=False)
	name = db.Column(db.String(50), nullable=False)
	is_verified = db.Column(db.Boolean, default=False)
	last_email_sent = db.Column(db.DateTime, nullable=True)

class Exam(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(100), nullable=False, unique=True)
	is_locked = db.Column(db.Boolean, default=False) # 新增：鎖定狀態防呆

class Score(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
	exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False)
	subject = db.Column(db.String(50), nullable=False)
	score = db.Column(db.Float, nullable=False)
	student = db.relationship('User', backref=db.backref('scores', cascade="all, delete-orphan"))
	exam = db.relationship('Exam', backref=db.backref('scores', cascade="all, delete-orphan"))

# ================= 輔助函數 (保留原有) =================
def is_strong_password(password):
	return re.match(r'^(?=.*[a-zA-Z])(?=.*\d)(?=.*[\W_]).{8,}$', password)

def mask_name(name):
	if not name: return ""
	if len(name) <= 2: return name[0] + "O"
	return name[0] + "O" * (len(name) - 2) + name[-1]

# (此處省略部分原有寄信邏輯，請將你原本的 check_and_update_email_cd 與 send_reset_email 貼回來)
def send_reset_email(user_email):
	reset_token = create_access_token(identity=user_email, additional_claims={'action': 'reset_password'}, expires_delta=datetime.timedelta(hours=1))
	msg = Message("系統登入與密碼設定通知", sender=app.config['MAIL_USERNAME'], recipients=[user_email])
	reset_link = f"http://localhost:5173/set-password?token={reset_token}"
	msg.body = f"請點擊以下連結設定您的密碼 (連結有效時間為 1 小時):\n\n{reset_link}"
	try: mail.send(msg); return True
	except: return False

def check_and_update_email_cd(user):
	now = datetime.datetime.now()
	if user.last_email_sent:
		diff = (now - user.last_email_sent).total_seconds()
		if diff < 60: return False, int(60 - diff)
	user.last_email_sent = now
	db.session.commit()
	return True, 0

# (此處省略 /login, /forgot-password, /set-password，請保留你原本的程式碼)
@app.route('/login', methods=['POST'])
def login():
	data = request.get_json()
	user = User.query.filter_by(email=data.get('email')).first()
	if not user: return jsonify({"msg": "帳號不存在"}), 404
	if not user.is_verified:
		can_send, wait_time = check_and_update_email_cd(user)
		if not can_send: return jsonify({"msg": f"信件發送太頻繁，請等待 {wait_time} 秒後再試"}), 429
		if send_reset_email(user.email): return jsonify({"msg": "此帳號尚未驗證，已發送設定密碼信件至您的 Email"}), 403
		return jsonify({"msg": "寄發驗證信失敗"}), 500
	if bcrypt.check_password_hash(user.password_hash, data.get('password')):
		access_token = create_access_token(identity=user.email, additional_claims={'role': user.role})
		return jsonify(access_token=access_token, role=user.role, name=user.name), 200
	return jsonify({"msg": "密碼錯誤"}), 401

@app.route('/forgot-password', methods=['POST'])
def forgot_password():
	user = User.query.filter_by(email=request.get_json().get('email')).first()
	if user:
		can_send, wait_time = check_and_update_email_cd(user)
		if not can_send:
			# 攔截 CD，回傳 429 讓前端捕捉
			return jsonify({"msg": f"發送太頻繁，請等待 {wait_time} 秒後再試"}), 429
		send_reset_email(user.email)
	
	# 為了防範信箱枚舉攻擊，無論信箱存不存在都回傳 200
	return jsonify({"msg": "如果該信箱存在，系統已寄出密碼重設信"}), 200
@app.route('/set-password', methods=['POST'])
@jwt_required()
def set_password():
	user = User.query.filter_by(email=get_jwt_identity()).first()
	new_pwd = request.json.get('password')
	if not is_strong_password(new_pwd): return jsonify({"msg": "密碼不符規定"}), 400
	user.password_hash = bcrypt.generate_password_hash(new_pwd).decode('utf-8')
	user.is_verified = True
	db.session.commit()
	return jsonify({"msg": "密碼設定成功，請重新登入"}), 200

# ================= 共用路由 =================
@app.route('/exams', methods=['GET'])
@jwt_required()
def get_exams():
	exams = Exam.query.all()
	# 把 is_locked 也傳給前端
	return jsonify([{"id": e.id, "name": e.name, "is_locked": e.is_locked} for e in exams]), 200

# ================= 學生專屬路由 =================
@app.route('/student/grades/<int:exam_id>', methods=['GET'])
@jwt_required()
def get_student_exam_grades(exam_id):
	email = get_jwt_identity()
	if get_jwt().get('role') != 'student': return jsonify({"msg": "權限不足"}), 403
	user = User.query.filter_by(email=email).first()
	
	# 取得全班這場考試的成績來計算排名與五標
	all_scores = Score.query.filter_by(exam_id=exam_id).all()
	if not all_scores:
		return jsonify({"student_id": user.student_id, "name": mask_name(user.name), "grades": None}), 200
		
	df = pd.DataFrame([{'student_id': s.student_id, 'subject': s.subject, 'score': s.score} for s in all_scores])
	
	# 1. 整理該學生的成績
	my_scores_df = df[df['student_id'] == user.id]
	my_grades = dict(zip(my_scores_df['subject'], my_scores_df['score']))
	my_total = round(my_scores_df['score'].sum(), 2)
	my_avg = round(my_scores_df['score'].mean(), 2) if not my_scores_df.empty else 0
	
	# 2. 計算全班各科五標
	standards = {}
	for subject, sub_df in df.groupby('subject'):
		standards[subject] = {
			"頂標": round(sub_df['score'].quantile(0.88), 2),
			"前標": round(sub_df['score'].quantile(0.75), 2),
			"均標": round(sub_df['score'].quantile(0.50), 2),
			"後標": round(sub_df['score'].quantile(0.25), 2),
			"底標": round(sub_df['score'].quantile(0.12), 2),
			"平均": round(sub_df['score'].mean(), 2)
		}
		
	# 3. 計算班排名 (依總分排序)
	totals = df.groupby('student_id')['score'].sum()
	ranks = totals.rank(ascending=False, method='min')
	my_rank = int(ranks.get(user.id, 0))
	total_students = len(totals)
	
	return jsonify({
		"student_id": user.student_id,
		"name": mask_name(user.name),
		"grades": my_grades,
		"total": my_total,
		"average": my_avg,
		"rank": my_rank,
		"total_students": total_students,
		"standards": standards
	}), 200

# ================= 老師專屬路由 =================
@app.route('/teacher/exams/<int:exam_id>', methods=['PUT'])
@jwt_required()
def update_exam(exam_id):
	if get_jwt().get('role') != 'teacher': return jsonify({"msg": "權限不足"}), 403
	exam = Exam.query.get_or_404(exam_id)
	data = request.get_json()
	
	if 'name' in data:
		# 檢查名稱是否重複
		existing = Exam.query.filter_by(name=data['name']).first()
		if existing and existing.id != exam_id:
			return jsonify({"msg": "此考試名稱已存在"}), 400
		exam.name = data['name']
		
	if 'is_locked' in data:
		exam.is_locked = data['is_locked']
		
	db.session.commit()
	return jsonify({"msg": "考試設定已更新"}), 200

@app.route('/teacher/exams/<int:exam_id>', methods=['DELETE'])
@jwt_required()
def delete_exam(exam_id):
	if get_jwt().get('role') != 'teacher': return jsonify({"msg": "權限不足"}), 403
	exam = Exam.query.get_or_404(exam_id)
	if exam.is_locked:
		return jsonify({"msg": "已鎖定的考試無法刪除，請先解除鎖定"}), 400
	
	db.session.delete(exam)
	db.session.commit()
	return jsonify({"msg": "考試場次與相關成績已刪除"}), 200

@app.route('/teacher/students/<int:exam_id>', methods=['GET'])
@jwt_required()
def get_all_students_for_exam(exam_id):
	if get_jwt().get('role') != 'teacher': return jsonify({"msg": "權限不足"}), 403
	students = User.query.filter_by(role='student').all()
	scores = Score.query.filter_by(exam_id=exam_id).all()
	
	# 將成績整理成 student_id -> {subject: score} 的字典
	score_map = {}
	for s in scores:
		if s.student_id not in score_map: score_map[s.student_id] = {}
		score_map[s.student_id][s.subject] = s.score

	result = []
	for st in students:
		result.append({
			"id": st.id, "student_id": st.student_id, "email": st.email,
			"name": st.name, "grades": score_map.get(st.id, {})
		})
	return jsonify(result), 200

@app.route('/teacher/students/<int:student_id>/<int:exam_id>', methods=['PUT'])
@jwt_required()
def update_student_grades(student_id, exam_id):
	if get_jwt().get('role') != 'teacher': return jsonify({"msg": "權限不足"}), 403
# 【防呆】檢查考試是否被鎖定
	exam = Exam.query.get_or_404(exam_id)
	if exam.is_locked:
		return jsonify({"msg": "此考試已鎖定，無法手動修改成績"}), 400
	data = request.get_json()
	
	# 更新基本資料
	student = User.query.get_or_404(student_id)
	if 'student_id' in data and data['student_id'] != student.student_id:
		student.student_id = data['student_id']
	if 'email' in data and data['email'] != student.email:
		student.email = data['email']
	if 'name' in data: student.name = data['name']
		
	# 動態更新成績
	if 'grades' in data:
		for subject, score_val in data['grades'].items():
			try:
				score_val = float(score_val)
				score_record = Score.query.filter_by(student_id=student.id, exam_id=exam_id, subject=subject).first()
				if score_record:
					score_record.score = score_val
				else:
					new_score = Score(student_id=student.id, exam_id=exam_id, subject=subject, score=score_val)
					db.session.add(new_score)
			except ValueError:
				pass # 略過非數字輸入

	db.session.commit()
	return jsonify({"msg": "更新成功"}), 200

@app.route('/teacher/import-grades', methods=['POST'])
@jwt_required()
def import_grades():
    if get_jwt().get('role') != 'teacher': return jsonify({"msg": "權限不足"}), 403
    if 'file' not in request.files: return jsonify({"msg": "請上傳檔案"}), 400
    
    file = request.files['file']
    try:
        sheets = pd.read_excel(file, sheet_name=None)
        total_inserted_scores = 0 
        total_upserted_students = 0
        deleted_count = 0 # 新增：記錄刪除了多少舊生
        
        # 步驟 1：優先處理「學生名單」Sheet (如果存在)
        if '學生名單' in sheets:
            df_students = sheets['學生名單']
            excel_student_ids = [] # 新增：用來記錄這份 Excel 裡面「有效」的學號
            
            for _, row in df_students.iterrows():
                s_id = str(row.get('學號', '')).strip()
                if s_id.endswith('.0'): s_id = s_id[:-2]
                if len(s_id) < 3 and s_id.isdigit(): s_id = s_id.zfill(3)
                
                email = str(row.get('Email', '')).strip()
                name = str(row.get('姓名', '')).strip()
                
                # 若缺少必填欄位則跳過
                if not s_id or not email or pd.isna(email) or not name or pd.isna(name):
                    continue
                    
                excel_student_ids.append(s_id) # 收集 Excel 裡的學號
                
                student = User.query.filter_by(student_id=s_id, role='student').first()
                if not student:
                    if not User.query.filter_by(email=email).first():
                        student = User(student_id=s_id, email=email, name=name, role='student', is_verified=False)
                        db.session.add(student)
                        total_upserted_students += 1
                else:
                    if student.email != email and not User.query.filter_by(email=email).first():
                        student.email = email
                    student.name = name
                    total_upserted_students += 1
            
            # 【關鍵修改】刪除資料庫中有，但 Excel 裡沒有的學生
            existing_students = User.query.filter_by(role='student').all()
            for db_student in existing_students:
                if db_student.student_id not in excel_student_ids:
                    db.session.delete(db_student)
                    deleted_count += 1

            # 先將學生名單 flush 到資料庫，以防後續成績找不到 user_id
            db.session.flush()

        # 步驟 2：處理各科考試的 Sheet
        for sheet_name, df in sheets.items():
            if sheet_name == '學生名單':
                continue
                
            if '學號' not in df.columns:
                return jsonify({"msg": f"工作表 '{sheet_name}' 缺少「學號」欄位，無法匯入成績"}), 400

            exam = Exam.query.filter_by(name=sheet_name).first()
            if not exam:
                exam = Exam(name=sheet_name)
                db.session.add(exam)
                db.session.flush()
            elif exam.is_locked:
                continue
            
            Score.query.filter_by(exam_id=exam.id).delete()
            
            for _, row in df.iterrows():
                student_id_val = str(row.get('學號', '')).strip()
                if student_id_val.endswith('.0'): student_id_val = student_id_val[:-2]
                if len(student_id_val) < 3 and student_id_val.isdigit(): student_id_val = student_id_val.zfill(3)

                student = User.query.filter_by(student_id=student_id_val, role='student').first()
                
                # 容錯機制：如果老師沒上傳名單，但成績單裡有附上姓名與 Email，直接幫忙建檔
                if not student:
                    email_val = str(row.get('Email', row.get('email', ''))).strip()
                    name_val = str(row.get('姓名', '')).strip()
                    if email_val and name_val and not pd.isna(email_val) and not pd.isna(name_val):
                        if not User.query.filter_by(email=email_val).first():
                            student = User(student_id=student_id_val, email=email_val, name=name_val, role='student', is_verified=False)
                            db.session.add(student)
                            db.session.flush()
                            total_upserted_students += 1
                
                if student:
                    for col in df.columns:
                        if col not in ['學號', '姓名', 'Email', 'email', '狀態'] and pd.notna(row.get(col)):
                            try:
                                score_val = float(row.get(col))
                                db.session.add(Score(student_id=student.id, exam_id=exam.id, subject=str(col), score=score_val))
                                total_inserted_scores += 1
                            except ValueError:
                                pass # 處理「缺考」或非數字字串

        # 判斷加上 deleted_count
        if total_inserted_scores == 0 and total_upserted_students == 0 and deleted_count == 0:
            db.session.rollback()
            return jsonify({"msg": "Excel 處理完畢，但未找到任何有效的學生或成績資料"}), 400

        db.session.commit()
        # 更新回傳訊息，讓前端顯示刪除人數
        return jsonify({"msg": f"匯入成功！更新 {total_upserted_students} 位學生，移除 {deleted_count} 位舊生，寫入 {total_inserted_scores} 筆成績"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"檔案解析發生錯誤: {str(e)}"}), 500
@app.route('/teacher/export-grades', methods=['GET'])
@jwt_required()
def export_grades():
    if get_jwt().get('role') != 'teacher': return jsonify({"msg": "權限不足"}), 403
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # 1. 獨立匯出「學生名單」Sheet
        students = User.query.filter_by(role='student').order_by(User.student_id).all()
        if students:
            df_students = pd.DataFrame([{
                '學號': s.student_id, 
                '姓名': s.name, 
                'Email': s.email,
                '狀態': '已開通' if s.is_verified else '未開通'
            } for s in students])
            df_students.to_excel(writer, index=False, sheet_name='學生名單')
        else:
            pd.DataFrame({"提示": ["系統尚無學生"]}).to_excel(writer, index=False, sheet_name='學生名單')

        # 2. 匯出各科成績
        exams = Exam.query.all()
        for exam in exams:
            scores = Score.query.filter_by(exam_id=exam.id).all()
            if not scores: continue
            df = pd.DataFrame([{
                '學號': s.student.student_id, 
                '姓名': s.student.name, 
                'Email': s.student.email, 
                'subject': s.subject, 
                'score': s.score
            } for s in scores])
            pivot_df = df.pivot_table(index=['學號', '姓名', 'Email'], columns='subject', values='score', aggfunc='first').reset_index()
            pivot_df.to_excel(writer, index=False, sheet_name=exam.name)
    
    output.seek(0)
    return send_file(output, download_name='school_data_export.xlsx', as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
def init_db():
	with app.app_context():
		inspector = inspect(db.engine)
		if not inspector.has_table("user"):
			db.create_all()
			teacher = User(email=app.config['MAIL_USERNAME'], role='teacher', name='Admin Teacher', is_verified=False)
			db.session.add(teacher)
			
			# 建立預設考試
			exam1 = Exam(name="第一次段考")
			exam2 = Exam(name="第二次段考")
			db.session.add_all([exam1, exam2])
			db.session.flush()

			for i in range(1, 10):
				s_id = f'{i:03d}'
				student = User(student_id=s_id, email=f'{s_id}@abc.edu.tw', role='student', name=f'學生{i}號', is_verified=False)
				db.session.add(student)
				db.session.flush()
				# 塞入隨機成績測試動態科目
				import random
				db.session.add(Score(student_id=student.id, exam_id=exam1.id, subject="國文", score=random.randint(40, 100)))
				db.session.add(Score(student_id=student.id, exam_id=exam1.id, subject="英文", score=random.randint(40, 100)))
				db.session.add(Score(student_id=student.id, exam_id=exam2.id, subject="基礎物理", score=random.randint(40, 100)))

			db.session.commit()
			print("資料庫初始化完成")
# ================= 獨立的學生名單管理 =================

@app.route('/teacher/all-students', methods=['GET'])
@jwt_required()
def get_all_students():
	if get_jwt().get('role') != 'teacher': return jsonify({"msg": "權限不足"}), 403
	students = User.query.filter_by(role='student').all()
	return jsonify([{
		"id": s.id, 
		"student_id": s.student_id, 
		"name": s.name, 
		"email": s.email, 
		"is_verified": s.is_verified
	} for s in students]), 200

@app.route('/teacher/student', methods=['POST'])
@jwt_required()
def add_student():
	if get_jwt().get('role') != 'teacher': return jsonify({"msg": "權限不足"}), 403
	data = request.get_json()
	
	# 防呆 1：檢查必填欄位
	if not data.get('student_id') or not data.get('email') or not data.get('name'):
		return jsonify({"msg": "學號、姓名與 Email 皆為必填"}), 400

	# 防呆 2：檢查重複
	if User.query.filter_by(student_id=data.get('student_id')).first():
		return jsonify({"msg": "此學號已存在系統中"}), 400
	if User.query.filter_by(email=data.get('email')).first():
		return jsonify({"msg": "此 Email 已被註冊"}), 400
		
	new_student = User(
		student_id=data.get('student_id'),
		email=data.get('email'),
		name=data.get('name'),
		role='student',
		is_verified=False # 預設未驗證，需透過忘記密碼設定
	)
	db.session.add(new_student)
	db.session.commit()
	return jsonify({"msg": "學生新增成功"}), 200

@app.route('/teacher/student/<int:student_id>', methods=['DELETE'])
@jwt_required()
def delete_student(student_id):
	if get_jwt().get('role') != 'teacher': return jsonify({"msg": "權限不足"}), 403
	student = User.query.get_or_404(student_id)
	
	# 防呆 3：檢查該學生是否有被「鎖定」的成績
	# 關聯 Score 與 Exam，如果該學生有成績且該考試 is_locked=True，則拒絕刪除
	locked_scores = Score.query.join(Exam).filter(Score.student_id == student.id, Exam.is_locked == True).first()
	if locked_scores:
		return jsonify({"msg": f"無法刪除！{student.name} 有參與已鎖定的考試，請先解鎖該考試才能刪除學生。"}), 400
	
	db.session.delete(student)
	db.session.commit()
	return jsonify({"msg": f"已成功刪除學生 {student.name} 及其所有未鎖定成績"}), 200
if __name__ == '__main__':
	init_db()
	app.run(debug=True, port=5000)
