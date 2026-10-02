import random
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash


# ============================================================
# 1. KHỞI TẠO FLASK
# ============================================================

app = Flask(__name__)

app.config['SECRET_KEY'] = 'bi-mat-do-an-tin-dung'

# ============================================================
# 2. CẤU HÌNH DATABASE SQLITE (ĐÃ FIX TỐI ƯU CHỐNG LOCK & CONTEXT ERROR)
# ============================================================
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///credit_system.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Tăng timeout chờ lock và bật trực tiếp chế độ WAL/Foreign Keys từ connect_args
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'connect_args': {
        'timeout': 30,
        'check_same_thread': False
    }
}
db = SQLAlchemy(app)
# Tự động đóng kết nối giải phóng lock sau mỗi request
@app.teardown_appcontext
def shutdown_session(exception=None):
    db.session.remove()

# ============================================================
# 3. CẤU HÌNH FLASK-LOGIN
# ============================================================
login_manager = LoginManager()
login_manager.init_app(app)

login_manager.login_view = 'login'
login_manager.login_message = "Vui lòng đăng nhập để truy cập hệ thống!"
login_manager.login_message_category = "warning"

# ============================================================
# 4. DATABASE MODEL - USER
# ============================================================
class User(UserMixin, db.Model):

    __tablename__ = 'users'

    id = db.Column(
        db.Integer,
        primary_key=True
    )
    username = db.Column(
        db.String(50),
        unique=True,
        nullable=False
        )
    password = db.Column(
        db.String(200),
        nullable=False
        )
    role = db.Column(
        db.String(20),
        nullable=False,
        default='user'
        )

# ============================================================
# 5. DATABASE MODEL - APPLICATION
# ============================================================
class Application(db.Model):
    __tablename__ = 'applications'
    id = db.Column(
        db.Integer,
        primary_key=True
    )
    app_id = db.Column(
        db.String(20),
        unique=True,
        nullable=False
    )
    username = db.Column(
        db.String(50),
        nullable=False
    )
    score = db.Column(
        db.Integer,
        nullable=False
    )
    # Lưu số tiền dưới dạng số để sau này dễ thống kê
    amount = db.Column(
        db.Float,
        nullable=False
    )
    status = db.Column(
        db.String(50),
        nullable=False
    )
    badge = db.Column(
        db.String(20),
        nullable=False
    )
    reject_reason = db.Column(db.Text, nullable=True)

# ============================================================
# 6. LOAD USER ĐĂNG NHẬP
# ============================================================
@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except (ValueError, TypeError):
        return None

# ============================================================
# 7. KHỞI TẠO DATABASE
# ============================================================
def init_db():
    with app.app_context():

        # Tạo bảng nếu chưa tồn tại
        db.create_all()

        # ----------------------------------------------------
        # Tạo tài khoản ADMIN mặc định
        # ----------------------------------------------------

        admin_user = User.query.filter_by(
            username='admin'
        ).first()

        if not admin_user:

            admin_user = User(
                username='admin',
                password=generate_password_hash(
                    'Admin2005@',
                    method='scrypt'
                ),
                role='admin'
            )

            db.session.add(admin_user)

        # ----------------------------------------------------
        # Tạo tài khoản USER mặc định
        # ----------------------------------------------------

        normal_user = User.query.filter_by(
            username='user'
        ).first()

        if not normal_user:

            normal_user = User(
                username='user',
                password=generate_password_hash(
                    '123456',
                    method='scrypt'
                ),
                role='user'
            )

            db.session.add(normal_user)

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()


# ============================================================
# 8. TRANG CHỦ
# ============================================================

@app.route('/')
@login_required
def home():

    if current_user.role == 'admin':

        return redirect(
            url_for('admin_dashboard')
        )

    return redirect(
        url_for('user_home')
    )


# ============================================================
# 9. TRANG NGƯỜI DÙNG
# ============================================================

@app.route('/user', methods=['GET', 'POST'])
@login_required
def user_home():

    result = None
    status = None
    reasons = []

    if request.method == 'POST':

        # ====================================================
        # KIỂM TRA DỮ LIỆU FORM
        # ====================================================

        try:

            income_text = request.form.get(
                'income',
                ''
            ).strip()

            credit_history_text = request.form.get(
                'credit_history',
                ''
            ).strip()

            loan_amount_text = request.form.get(
                'loan_amount',
                ''
            ).strip()

            age_text = request.form.get(
                'age',
                ''
            ).strip()

            # Không cho phép bỏ trống
            if not income_text:
                raise ValueError("Thu nhập không được để trống.")

            if not credit_history_text:
                raise ValueError(
                    "Vui lòng chọn lịch sử tín dụng."
                )

            if not loan_amount_text:
                raise ValueError(
                    "Số tiền vay không được để trống."
                )

            if not age_text:
                raise ValueError(
                    "Tuổi không được để trống."
                )

            # Chuyển kiểu dữ liệu
            income = float(income_text)

            credit_history = int(
                credit_history_text
            )

            loan_amount = float(
                loan_amount_text
            )

            age = int(age_text)

        except ValueError as e:

            flash(
                f"Dữ liệu không hợp lệ: {e}",
                'danger'
            )

            return redirect(
                url_for('user_home')
            )

        # ====================================================
        # KIỂM TRA DỮ LIỆU ÂM / KHÔNG HỢP LỆ
        # ====================================================

        if income <= 0:

            flash(
                'Thu nhập phải lớn hơn 0.',
                'danger'
            )

            return redirect(
                url_for('user_home')
            )

        if loan_amount <= 0:

            flash(
                'Số tiền vay phải lớn hơn 0.',
                'danger'
            )

            return redirect(
                url_for('user_home')
            )

        if age <= 0:

            flash(
                'Tuổi phải lớn hơn 0.',
                'danger'
            )

            return redirect(
                url_for('user_home')
            )

        # ====================================================
        # KIỂM TRA LỊCH SỬ TÍN DỤNG
        # ====================================================

        if credit_history not in [0, 1]:

            flash(
                'Lịch sử tín dụng không hợp lệ.',
                'danger'
            )

            return redirect(
                url_for('user_home')
            )

       # ====================================================
        # KIỂM TRA ĐIỀU KIỆN VAY (CẬP NHẬT QUY ĐỊNH MỚI)
        # ====================================================
        # 1. Kiểm tra lịch sử tín dụng
        if credit_history == 0:
            reasons.append(
                "Lịch sử tín dụng có nợ xấu (Yêu cầu lịch sử tín dụng tốt)."
            )
        # 2. Kiểm tra thu nhập (Tối thiểu 5 triệu VNĐ)
        if income < 5:
            reasons.append(
                f"Thu nhập hàng tháng quá thấp ({income:,.1f} triệu VNĐ - Yêu cầu tối thiểu từ 5 triệu VNĐ)."
            )
        # 3. Kiểm tra số tiền vay (Tối thiểu 10 triệu, Tối đa 1,000 triệu = 1 tỷ)
        if loan_amount < 10:
            reasons.append(
                f"Số tiền muốn vay quá nhỏ ({loan_amount:,.0f} triệu VNĐ - Yêu cầu vay tối thiểu từ 10 triệu VNĐ)."
            )
        elif loan_amount > 1000:
            reasons.append(
                f"Số tiền muốn vay quá lớn ({loan_amount:,.0f} triệu VNĐ - Yêu cầu vay tối đa 1,000 triệu VNĐ / 1 tỷ VNĐ)."
            )
        # 4. Kiểm tra tỷ lệ vay so với thu nhập (Tối đa 20 lần thu nhập)
        max_loan_by_income = income * 20
        if loan_amount > max_loan_by_income and loan_amount <= 1000:
            reasons.append(
                f"Số tiền vay ({loan_amount:,.0f} triệu VNĐ) vượt quá hạn mức theo thu nhập "
                f"(Tối đa {max_loan_by_income:,.0f} triệu VNĐ tương ứng 20 lần thu nhập)."
            )
        # 5. Kiểm tra độ tuổi
        if age < 18 or age > 60:
            reasons.append(
                f"Độ tuổi ({age} tuổi) ngoài quy định (Từ 18 đến 60 tuổi)."
            )
        # ====================================================
        # ĐÁNH GIÁ HỒ SƠ
        if len(reasons) == 0:
            status = 1
            result = (
                "Hồ sơ ĐỦ ĐIỀU KIỆN cho vay! "
                "(Approved)"
            )
            ai_status = "Phê Duyệt"
            badge_type = "approved"
        else:
            status = 0
            result = (
                "Hồ sơ KHÔNG ĐỦ ĐIỀU KIỆN cho vay! "
                "(Rejected)"
            )
            ai_status = "Từ Chối"
            badge_type = "rejected"
        # ====================================================
        # TẠO ĐIỂM TÍN DỤNG DEMO
       
        if status == 1:
            score = random.randint(
                650,
                850
            )
        else:
            score = random.randint(
                400,
                649
            )
        # ====================================================
        # TẠO HỒ SƠ MỚI (ĐÃ FIX LỖI DATABASE LOCKED)
        # 1. Sinh mã ngẫu nhiên và kiểm tra trùng TRƯỚC KHI add vào session
        generated_app_id = f"HS-{random.randint(100000, 999999)}"
        while Application.query.filter_by(app_id=generated_app_id).first():
            generated_app_id = f"HS-{random.randint(100000, 999999)}"
        # 2. Khởi tạo đối tượng hồ sơ
        new_app = Application(
            app_id=generated_app_id,
            username=current_user.username,
            score=score,
            amount=loan_amount,
            status=ai_status,
            badge=badge_type
        )
        # 3. Lưu vào Database với try-except an toàn
        try:
            db.session.add(new_app)
            db.session.commit()
            if status == 1:
                flash(
                    "Đã lưu hồ sơ vay thành công.",
                    "success"
                )
            else:
                flash(
                    "Hồ sơ đã được lưu vào hệ thống.",
                    "warning"
                )
        except Exception as e:
            db.session.rollback()
            flash(
                f"Lỗi khi lưu dữ liệu vào hệ thống: {e}",
                "danger"
            )
    # ========================================================
    # HIỂN THỊ GIAO DIỆN
    user_app = Application.query.filter_by(username=current_user.username).order_by(Application.id.desc()).first()

    return render_template(
        'index.html',
        result=result,
        status=status,
        reasons=reasons,
        user=current_user,
        application=user_app
    )

# ============================================================
# ============================================================
# 10. ADMIN DASHBOARD & QUẢN LÝ NGƯỜI DÙNG
# ============================================================
@app.route('/admin')
@login_required
def admin_dashboard():
    # Kiểm tra quyền Admin
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập trang Admin!', 'danger')
        return redirect(url_for('user_home'))

    # Lấy danh sách hồ sơ vay
    applications = Application.query.order_by(Application.id.desc()).all()
    
    # Lấy danh sách tất cả tài khoản người dùng
    all_users = User.query.all()

    # Thống kê
    total_activities = Application.query.count()
    total_users = User.query.count()
    total_loans = sum(item.amount for item in applications)
    approved_count = Application.query.filter_by(status='Phê Duyệt').count()
    rejected_count = Application.query.filter_by(status='Từ Chối').count()

    # Tính tỷ lệ phê duyệt
    if total_activities > 0:
        approval_rate = round((approved_count / total_activities) * 100, 1)
    else:
        approval_rate = 0
    return render_template(
        'admin.html',
        user=current_user,
        apps=applications,
        users_list=all_users,  # <-- Thêm biến này để gửi danh sách user sang admin.html
        total_activities=total_activities,
        total_users=total_users,
        total_loans=total_loans,
        approval_rate=approval_rate,
        approved_count=approved_count,
        rejected_count=rejected_count
    )

# API Xóa người dùng (Dành cho Admin)
@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        flash('Bạn không có quyền thực hiện thao tác này!', 'danger')
        return redirect(url_for('user_home'))

    user_to_delete = db.session.get(User, user_id)
    if user_to_delete:
        if user_to_delete.username == 'admin':
            flash('Không thể xóa tài khoản Admin mặc định!', 'warning')
        else:
            db.session.delete(user_to_delete)
            db.session.commit()
            flash(f'Đã xóa tài khoản {user_to_delete.username} thành công.', 'success')
    else:
        flash('Tài khoản không tồn tại!', 'danger')

    return redirect(url_for('admin_dashboard'))

# ============================================================
# 11. ĐĂNG NHẬP
# ============================================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get(
            'username', ''
        ).strip()
        password = request.form.get(
            'password',''
        )
        if not username or not password:
            flash(
                'Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu!',
                'danger'
            )
            return redirect(
                url_for('login')
            )
        user = User.query.filter_by(
            username=username
        ).first()

        if user and check_password_hash(
            user.password,
            password
        ):
            login_user(user)
            return redirect(
                url_for('home')
            )
        else:
            flash(
                'Tên đăng nhập hoặc mật khẩu không chính xác!',
                'danger'
            )
    return render_template(
        'login.html'
    )

# ============================================================
# 12. ĐĂNG KÝ
# ============================================================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get(
            'username', ''
        ).strip()
        password = request.form.get(
            'password', ''
        )
        if not username:
            flash(
                'Tên đăng nhập không được để trống!',
                'danger'
            )
            return redirect(
                url_for('register')
            )
        if not password:
            flash(
                'Mật khẩu không được để trống!',
                'danger'
            )
            return redirect(
                url_for('register')
            )
        if len(username) < 3:
            flash(
                'Tên đăng nhập phải có ít nhất 3 ký tự!',
                'danger'
            )
            return redirect(
                url_for('register')
            )
        if len(password) < 6:
            flash(
                'Mật khẩu phải có ít nhất 6 ký tự!',
                'danger'
            )
            return redirect(
                url_for('register')
            )
        existing_user = User.query.filter_by(
            username=username
        ).first()
        if existing_user:
            flash(
                'Tên đăng nhập này đã tồn tại!',
                'danger'
            )
            return redirect(
                url_for('register')
            )
        new_user = User(
            username=username,
            password=generate_password_hash(
                password,
                method='scrypt'
            ),
            role='user'
        )
        try:
            db.session.add(new_user)
            db.session.commit()
            flash(
                'Đăng ký thành công! Hãy đăng nhập.',
                'success'
            )
            return redirect(
                url_for('login')
            )
        except Exception as e:
            db.session.rollback()
            flash(
                f"Có lỗi xảy ra trong quá trình đăng ký: {e}",
                'danger'
            )
    return render_template(
        'register.html'
    )

# ============================================================
# 13. ĐĂNG XUẤT
# ============================================================
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash(
        'Đã đăng xuất thành công.',
        'info'
    )
    return redirect(
        url_for('login')
    )

# ============================================================
# Bổ sung tự động update tổng tiền 
# ============================================================
@app.template_filter('format_money')
def format_money(value):
    if value is None:
        return "0 VNĐ"
    try:
        # Làm sạch chuỗi nếu dữ liệu chứa dấu phẩy hoặc khoảng trắng
        if isinstance(value, str):
            value = value.replace(',', '').strip()

        val = float(value)
    except (ValueError, TypeError):
        return "0 VNĐ"

    # LƯU Ý: Nếu dữ liệu trong Database của bạn đang lưu theo đơn vị TRIỆU 
    # (Ví dụ: 1650 = 1,650 triệu = 1.65 tỷ), hãy BỎ DẤU # ở dòng bên dưới:
    # val = val * 1_000_000
    abs_val = abs(val)
    if abs_val >= 1e15:
        amount = val / 1e15
        unit = "triệu tỷ VNĐ"
    elif abs_val >= 1e12:
        amount = val / 1e12
        unit = "nghìn tỷ VNĐ"
    elif abs_val >= 1e9:
        amount = val / 1e9
        unit = "tỷ VNĐ"
    elif abs_val >= 1e6:
        amount = val / 1e6
        unit = "triệu VNĐ"
    elif abs_val >= 1e3:
        amount = val / 1e3
        unit = "nghìn VNĐ"
    else:
        return f"{int(val):,} VNĐ".replace(',', '.')

    # Làm tròn 2 chữ số thập phân và định dạng dấu phẩy tiếng Việt
    formatted_amount = f"{amount:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    
    if formatted_amount.endswith(',00'):
        formatted_amount = formatted_amount[:-3]
    return f"{formatted_amount} {unit}"

# ==============================================================================
# ROUTE XỬ LÝ PHÊ DUYỆT / TỪ CHỐI HỒ SƠ
# ==============================================================================
@app.route('/approve_application/<int:id>', methods=['POST'])
@login_required
def approve_application(id):
    app_item = Application.query.get_or_404(id)
    app_item.status = 'Đã Phê Duyệt'
    db.session.commit()
    flash('Đã phê duyệt hồ sơ thành công!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/reject_application/<int:id>', methods=['POST'])
@login_required
def reject_application(id):
    app_item = Application.query.get_or_404(id)
    reason = request.form.get('reject_reason', 'Không đủ điều kiện phê duyệt')
    
    app_item.status = 'Từ Chối'
    app_item.reject_reason = reason
    db.session.commit()
    flash('Đã từ chối hồ sơ và gửi phản hồi cho khách hàng.', 'warning')
    return redirect(url_for('admin_dashboard'))

# ==============================================================================
# ROUTE YÊU CẦU BỔ SUNG THÔNG TIN HỒ SƠ
@app.route('/request_info_application/<int:id>', methods=['POST'])
@login_required
def request_info_application(id):
    app_item = Application.query.get_or_404(id)
    info_needed = request.form.get('info_needed', 'Cần bổ sung thêm thông tin giấy tờ/thu nhập.')
    
    app_item.status = 'Cần Bổ Sung'
    app_item.badge = 'pending'
    app_item.reject_reason = info_needed  # Lưu lý do/yêu cầu bổ sung vào biến này
    db.session.commit()
    
    flash('Đã gửi yêu cầu bổ sung thông tin đến khách hàng!', 'info')
    return redirect(url_for('admin_dashboard'))
# ============================================================
# 14. CHẠY ỨNG DỤNG
# ============================================================
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)