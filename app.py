from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'bi-mat-do-an-tin-dung'

# Cấu hình hệ thống Đăng nhập
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Vui lòng đăng nhập để sử dụng ứng dụng!"

# Bộ nhớ lưu tài khoản tạm thời
users = {}

class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    if user_id in users:
        return User(user_id, users[user_id]['username'])
    return None

# 1. TRANG CHỦ DỰ ĐOÁN (Chỉ vào được khi đã đăng nhập)
@app.route('/', methods=['GET', 'POST'])
@login_required
def home():
    result = None
    status = None
    reasons = [] # Lưu danh sách các lý do bị từ chối

    if request.method == 'POST':
        income = float(request.form.get('income', 0))
        credit_history = int(request.form.get('credit_history', 0))
        loan_amount = float(request.form.get('loan_amount', 0))
        age = int(request.form.get('age', 0))

        # Kiểm tra từng điều kiện tiêu chuẩn
        if credit_history == 0:
            reasons.append("Lịch sử tín dụng có nợ xấu (Cần lịch sử tín dụng Tốt).")
        
        if income < 10:
            reasons.append(f"Thu nhập hàng tháng quá thấp ({income} triệu - Yêu cầu tối thiểu từ 10 triệu/tháng).")
            
        if loan_amount > (income * 20):
            reasons.append(f"Số tiền muốn vay ({loan_amount} triệu) vượt quá hạn mức cho phép (Tối đa {income * 20} triệu - tương đương 20 lần thu nhập).")
            
        if age < 18 or age > 60:
            reasons.append(f"Độ tuổi ({age} tuổi) không nằm trong quy định cho vay (Từ 18 đến 60 tuổi).")

        # Đánh giá kết quả
        if len(reasons) == 0:
            status = 1
            result = "Hồ sơ ĐỦ ĐIỀU KIỆN cho vay! (Approved)"
        else:
            status = 0
            result = "Hồ sơ KHÔNG ĐỦ ĐIỀU KIỆN cho vay! (Rejected)"

    return render_template('index.html', result=result, status=status, reasons=reasons, user=current_user)

# 2. ROUTE DỰ ĐOÁN (Chuyển lên trước app.run)
@app.route('/predict', methods=['POST'])
@login_required
def predict():
    income = float(request.form.get('income', 0))
    credit_history = int(request.form.get('credit_history', 0))
    loan_amount = float(request.form.get('loan_amount', 0))

    if credit_history == 1 and income >= 10 and loan_amount <= (income * 20):
        status = 1
        result = "Hồ sơ ĐỦ ĐIỀU KIỆN cho vay! (Approved)"
    else:
        status = 0
        result = "Hồ sơ KHÔNG ĐỦ ĐIỀU KIỆN cho vay! (Rejected)"

    return render_template('index.html', result=result, status=status, user=current_user)

# 3. TRANG ĐĂNG KÝ
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username in users:
            flash('Tên đăng nhập này đã tồn tại!', 'danger')
            return redirect(url_for('register'))

        users[username] = {
            'username': username,
            'password': generate_password_hash(password, method='scrypt')
        }

        flash('Đăng ký tài khoản thành công! Vui lòng đăng nhập.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

# 4. TRANG ĐĂNG NHẬP
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user_data = users.get(username)
        if user_data and check_password_hash(user_data['password'], password):
            user = User(id=username, username=username)
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Tên đăng nhập hoặc mật khẩu không chính xác!', 'danger')

    return render_template('login.html')

# 5. ĐĂNG XUẤT
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Đã đăng xuất tài khoản.', 'info')
    return redirect(url_for('login'))

# LỆNH CHẠY SERVER LUÔN ĐẶT Ở CUỐI FILE
if __name__ == '__main__':
    app.run(debug=True)