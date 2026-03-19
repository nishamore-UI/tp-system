import csv
from flask import Response
import io
from collections import Counter
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import Student, Admin
from extensions import db
from sqlalchemy import or_


routes = Blueprint("routes", __name__)

# ---------------- HOME ----------------
@routes.route("/")
def home():
    if "admin" not in session:
        return redirect(url_for("routes.login"))

    total_students = Student.query.count()
    placed_students = Student.query.filter_by(placement_status="Placed").count()
    not_placed_students = Student.query.filter_by(placement_status="Not Placed").count()

    return render_template(
        "home.html",
        total=total_students,
        placed=placed_students,
        not_placed=not_placed_students
    )


# ---------------- STUDENTS ----------------
@routes.route("/students")
def students():
    return redirect(url_for("routes.dashboard"))


# ---------------- ADD STUDENT ----------------
@routes.route("/add-student", methods=["GET", "POST"])
def add_student():

    if "user" not in session:
        return redirect(url_for("routes.login"))

    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        course = request.form.get("course")
        placement_status = request.form.get("placement_status")

        student = Student(
            name=name,
            email=email,
            course=course,
            placement_status=placement_status
        )

        db.session.add(student)
        db.session.commit()

        flash("Student added successfully!", "success")
        
        return redirect(url_for("routes.dashboard"))

    return render_template("add_student.html")


# ---------------- DELETE STUDENT ----------------
@routes.route("/delete-student/<int:id>")
def delete_student(id):

    # 🔐 Must be logged in
    if "user" not in session:
        return redirect(url_for("routes.login"))

    # 🔒 Only admin can delete
    if session.get("role") != "admin":
        flash("You are not authorized to delete students.", "danger")
        return redirect(url_for("routes.dashboard"))

    student = Student.query.get(id)

    if student:
        db.session.delete(student)
        db.session.commit()
        flash("Student deleted successfully!", "danger")

    return redirect(url_for("routes.dashboard"))



# ---------------- EDIT STUDENT ----------------
@routes.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_student(id):
    student = Student.query.get_or_404(id)

    if request.method == 'POST':
        student.name = request.form['name']
        student.email = request.form['email']
        student.course = request.form['course']
        student.placement_status = request.form['placement_status']   # ← ADD THIS

        db.session.commit()

        flash("Student Updated successfully!", "danger")

        return redirect(url_for('routes.students'))

    return render_template('edit_student.html', student=student)




# ---------------- LOGIN ----------------
@routes.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = Admin.query.filter_by(username=username).first()

        if user and user.password == password:

            session["user"] = user.username
            session["role"] = user.role

            return redirect(url_for("routes.dashboard"))

        else:
            flash("Invalid credentials", "danger")

    return render_template("login.html")


# ---------------- LOGOUT ----------------
@routes.route("/logout")
def logout():
    session.pop("user", None)
    session.pop("role", None)

    return redirect(url_for("routes.login"))

# -----------------Dashboard--------------------
@routes.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect(url_for("routes.login"))

    search_query = request.args.get("search")
    filter_status = request.args.get("filter")

    print("FILTER STATUS:", filter_status)

    current_filter = request.args.get("filter", "All")
    course_filter = request.args.get("course", "All")

    query = Student.query

    # Course filter
    if course_filter != "All":
        query = query.filter(Student.course == course_filter)

    # ✅ Placement Status filter (ADD THIS)
    if filter_status and filter_status != "All":
        query = query.filter(Student.placement_status == filter_status)
    # Search
    if search_query:
        query = query.filter(
            or_(
                Student.name.ilike(f"%{search_query}%"),
                Student.email.ilike(f"%{search_query}%"),
                Student.course.ilike(f"%{search_query}%")
            )
        )

    page = request.args.get('page', 1, type=int)
    students = query.paginate(page=page, per_page=5)

    total_students = Student.query.count()
    placed_students = Student.query.filter_by(placement_status="Placed").count()
    not_placed_students = Student.query.filter_by(placement_status="Not Placed").count()

    if total_students > 0:
        placement_percentage = round((placed_students / total_students) * 100, 2)
    else:
        placement_percentage = 0

    # Course list for filters
    courses = db.session.query(Student.course).distinct().all()
    courses = [c[0] for c in courses]

    from collections import Counter

    course_data = Counter()
    all_students = Student.query.all()

    for student in all_students:
        if student.placement_status == "Placed":
            course_data[student.course] += 1

    course_labels = list(course_data.keys())
    course_values = list(course_data.values())

    return render_template(
    "dashboard.html",
    students=students,
    total_students=total_students,
    placed_students=placed_students,
    not_placed_students=not_placed_students,
    placement_percentage=placement_percentage,
    current_filter=current_filter,
    courses=courses,
    course_filter=course_filter,
    course_labels=course_labels,
    course_values=course_values,
    search_query=search_query
)


from flask import Response, request
import csv
import io

@routes.route("/export")
def export_students():

    if "user" not in session:
        return redirect(url_for("routes.login"))

    # Filters
    course = request.args.get("course", "All")
    status = request.args.get("filter", "All")
    search = request.args.get("search")

    query = Student.query

    if course != "All":
        query = query.filter(Student.course == course)

    if status != "All":
        query = query.filter(Student.placement_status == status)

    if search:
        query = query.filter(
            or_(
                Student.name.ilike(f"%{search}%"),
                Student.email.ilike(f"%{search}%"),
                Student.course.ilike(f"%{search}%")
            )
        )

    students = query.all()

    # ✅ VERY IMPORTANT (THIS FIXES YOUR ERROR)
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(['Name', 'Email', 'Course', 'Status'])

    # Data
    for student in students:
        writer.writerow([
            student.name,
            student.email,
            student.course,
            student.placement_status
        ])

    # Filename
    status_clean = status.replace(" ", "")
    filename = f"students_{course}_{status_clean}.csv"

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

    
@routes.route("/import", methods=["GET", "POST"])
def import_students():

    if "user" not in session:
        return redirect(url_for("routes.login"))

    if request.method == "POST":

        file = request.files["file"]

        if file:
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            reader = csv.DictReader(stream)

            for row in reader:
                student = Student(
                    name=row["name"],
                    email=row["email"],
                    course=row["course"],
                    placement_status=row["placement_status"]
                )

                db.session.add(student)

            db.session.commit()

            flash("Students imported successfully!", "success")
            return redirect(url_for("routes.dashboard"))

    return render_template("import_students.html")