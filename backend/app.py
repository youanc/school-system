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
		if can_send: send_reset_email(user.email)
	return jsonify({"msg": "若該信箱存在，系統已發送密碼重設信"}), 200

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
		# sheet_name=None 讀取所有工作表
		sheets = pd.read_excel(file, sheet_name=None)
		
		for sheet_name, df in sheets.items():
			exam = Exam.query.filter_by(name=sheet_name).first()
			if not exam:
				exam = Exam(name=sheet_name)
				db.session.add(exam)
				db.session.flush()
			else:
				# 【防呆】如果考試存在且已被鎖定，跳過這個 sheet 不匯入
				if exam.is_locked:
					continue
			
			# 清除該考試舊成績以利覆蓋
			Score.query.filter_by(exam_id=exam.id).delete()
			
			for _, row in df.iterrows():
				student_id_val = str(row.get('學號', '')).strip()
				if student_id_val.endswith('.0'): student_id_val = student_id_val[:-2]
				if len(student_id_val) < 3 and student_id_val.isdigit(): student_id_val = student_id_val.zfill(3)

				student = User.query.filter_by(student_id=student_id_val, role='student').first()
				if student:
					# 動態寫入所有科目 (排除學號、姓名、Email等)
					for col in df.columns:
						if col not in ['學號', '姓名', 'Email', 'email'] and pd.notna(row.get(col)):
							db.session.add(Score(student_id=student.id, exam_id=exam.id, subject=str(col), score=float(row.get(col))))
		db.session.commit()
		return jsonify({"msg": "多場考試匯入成功"}), 200
	except Exception as e:
		return jsonify({"msg": f"匯入失敗: {str(e)}"}), 500

@app.route('/teacher/export-grades', methods=['GET'])
@jwt_required()
def export_grades():
	if get_jwt().get('role') != 'teacher': return jsonify({"msg": "權限不足"}), 403
	
	exams = Exam.query.all()
	output = io.BytesIO()
	with pd.ExcelWriter(output, engine='openpyxl') as writer:
		if not exams:
			pd.DataFrame({"提示": ["尚無資料"]}).to_excel(writer, index=False, sheet_name='無資料')
		else:
			for exam in exams:
				scores = Score.query.filter_by(exam_id=exam.id).all()
				if not scores: continue
				# 將成績轉為 DataFrame 並做 Pivot Table 展開科目
				df = pd.DataFrame([{'學號': s.student.student_id, '姓名': s.student.name, 'Email': s.student.email, 'subject': s.subject, 'score': s.score} for s in scores])
				pivot_df = df.pivot_table(index=['學號', '姓名', 'Email'], columns='subject', values='score', aggfunc='first').reset_index()
				pivot_df.to_excel(writer, index=False, sheet_name=exam.name)
	
	output.seek(0)
	return send_file(output, download_name='all_exams_grades.xlsx', as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

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

if __name__ == '__main__':
	init_db()
	app.run(debug=True, port=5000)