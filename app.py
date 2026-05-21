from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    flash,
    redirect,
    url_for,
    Response,
    session,
)
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import json
import random
import os

# Import translations
from translations import get_translation, get_available_languages, t as translate

app = Flask(__name__)
app.config["SECRET_KEY"] = "hospital-triage-secret-key-2024"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///hospital.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ==================== I18N SETUP ====================


@app.before_request
def set_language():
    """Set language from URL param, session, or browser header."""
    # Check URL parameter first
    lang = request.args.get("lang")
    if lang and lang in ["en", "vi"]:
        session["lang"] = lang
        return

    # Check session
    if "lang" in session:
        return

    # Check browser Accept-Language header
    browser_lang = request.accept_languages.best_match(["vi", "en"])
    session["lang"] = browser_lang if browser_lang else "vi"


@app.context_processor
def inject_translations():
    """Inject translation function into all templates."""

    def t(key):
        return translate(key, session.get("lang", "vi"))

    return dict(
        t=t,
        current_lang=session.get("lang", "vi"),
        available_languages=get_available_languages(),
    )


@app.route("/set_language/<lang>")
def set_language_route(lang):
    """Switch language and redirect back."""
    if lang in ["en", "vi"]:
        session["lang"] = lang
        flash(
            f"Language switched to {get_available_languages()[0 if lang == 'vi' else 1]['name']}",
            "success",
        )

    # Redirect back to referring page or dashboard
    next_page = request.referrer or url_for("dashboard")
    return redirect(next_page)


# ==================== DATABASE MODELS ====================


class Department(db.Model):
    __tablename__ = "departments"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    capacity = db.Column(db.Integer, default=20)
    current_patients = db.Column(db.Integer, default=0)
    doctors = db.relationship("Doctor", backref="department", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "capacity": self.capacity,
            "current_patients": self.current_patients,
            "queue_length": len(
                [
                    p
                    for p in self.doctors
                    for a in p.appointments
                    if a.status == "scheduled"
                ]
            ),
            "available_doctors": len(
                [d for d in self.doctors if d.status == "available"]
            ),
        }


class Doctor(db.Model):
    __tablename__ = "doctors"
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True)
    phone = db.Column(db.String(20))
    specialty = db.Column(db.String(100))
    status = db.Column(db.String(20), default="available")  # available, busy, off-duty
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"))
    appointments = db.relationship("Appointment", backref="doctor", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": f"{self.first_name} {self.last_name}",
            "email": self.email,
            "phone": self.phone,
            "specialty": self.specialty,
            "status": self.status,
            "department_id": self.department_id,
            "department_name": self.department.name if self.department else None,
        }


class Patient(db.Model):
    __tablename__ = "patients"
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    date_of_birth = db.Column(db.Date)
    gender = db.Column(db.String(10))
    address = db.Column(db.Text)
    emergency_contact = db.Column(db.String(100))
    blood_type = db.Column(db.String(5))
    allergies = db.Column(db.Text)
    medical_history = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default="active")  # active, discharged, emergency
    priority = db.Column(db.Integer, default=3)  # 1=critical, 2=urgent, 3=normal, 4=low
    appointments = db.relationship("Appointment", backref="patient", lazy=True)
    bills = db.relationship("Bill", backref="patient", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": f"{self.first_name} {self.last_name}",
            "email": self.email,
            "phone": self.phone,
            "date_of_birth": self.date_of_birth.isoformat()
            if self.date_of_birth
            else None,
            "gender": self.gender,
            "address": self.address,
            "emergency_contact": self.emergency_contact,
            "blood_type": self.blood_type,
            "allergies": self.allergies,
            "medical_history": self.medical_history,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "status": self.status,
            "priority": self.priority,
        }


class Appointment(db.Model):
    __tablename__ = "appointments"
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False)
    appointment_date = db.Column(db.DateTime, nullable=False)
    duration = db.Column(db.Integer, default=30)  # minutes
    status = db.Column(
        db.String(20), default="scheduled"
    )  # scheduled, checked-in, in-progress, completed, cancelled
    type = db.Column(
        db.String(50), default="consultation"
    )  # consultation, follow-up, emergency, routine
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "patient_name": self.patient.full_name if self.patient else None,
            "doctor_id": self.doctor_id,
            "doctor_name": self.doctor.full_name if self.doctor else None,
            "appointment_date": self.appointment_date.isoformat()
            if self.appointment_date
            else None,
            "duration": self.duration,
            "status": self.status,
            "type": self.type,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Bill(db.Model):
    __tablename__ = "bills"
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200))
    status = db.Column(db.String(20), default="pending")  # pending, paid, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    paid_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "patient_name": f"{self.patient.first_name} {self.patient.last_name}"
            if self.patient
            else None,
            "amount": self.amount,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
        }


class QueueEntry(db.Model):
    __tablename__ = "queue_entries"
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    department_id = db.Column(
        db.Integer, db.ForeignKey("departments.id"), nullable=False
    )
    priority = db.Column(db.Integer, default=3)
    status = db.Column(
        db.String(20), default="waiting"
    )  # waiting, in-progress, completed
    checked_in_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)

    # Relationships
    patient = db.relationship("Patient", backref="queue_entries", lazy=True)
    department = db.relationship("Department", backref="queue_entries", lazy=True)

    @property
    def patient_name(self):
        if self.patient:
            return f"{self.patient.first_name} {self.patient.last_name}"
        return "Unknown"

    @property
    def department_name(self):
        if self.department:
            return self.department.name
        return "Unknown"

    @property
    def wait_time(self):
        if self.checked_in_at:
            return int((datetime.utcnow() - self.checked_in_at).total_seconds() // 60)
        return 0

    def to_dict(self):
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "patient_name": self.patient_name,
            "department_id": self.department_id,
            "department_name": self.department_name,
            "priority": self.priority,
            "status": self.status,
            "checked_in_at": self.checked_in_at.isoformat()
            if self.checked_in_at
            else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "wait_time": self.wait_time,
        }


# ==================== INITIALIZE DATABASE ====================


def init_db():
    with app.app_context():
        db.create_all()

        # Add sample departments if none exist
        if Department.query.count() == 0:
            departments = [
                Department(name="Emergency Room", code="ER", capacity=30),
                Department(name="General Medicine", code="GM", capacity=50),
                Department(name="Pediatrics", code="PED", capacity=25),
                Department(name="Cardiology", code="CAR", capacity=20),
                Department(name="Orthopedics", code="ORT", capacity=20),
                Department(name="Radiology", code="RAD", capacity=15),
                Department(name="Laboratory", code="LAB", capacity=20),
                Department(name="Surgery", code="SUR", capacity=15),
            ]
            db.session.add_all(departments)
            db.session.commit()

        # Add sample doctors if none exist
        if Doctor.query.count() == 0:
            doctors = [
                Doctor(
                    first_name="John",
                    last_name="Smith",
                    email="jsmith@hospital.com",
                    specialty="Emergency Medicine",
                    status="available",
                    department_id=1,
                ),
                Doctor(
                    first_name="Sarah",
                    last_name="Johnson",
                    email="sjohnson@hospital.com",
                    specialty="General Practice",
                    status="available",
                    department_id=2,
                ),
                Doctor(
                    first_name="Michael",
                    last_name="Brown",
                    email="mbrown@hospital.com",
                    specialty="Pediatrics",
                    status="busy",
                    department_id=3,
                ),
                Doctor(
                    first_name="Emily",
                    last_name="Davis",
                    email="edavis@hospital.com",
                    specialty="Cardiology",
                    status="available",
                    department_id=4,
                ),
                Doctor(
                    first_name="Robert",
                    last_name="Wilson",
                    email="rwilson@hospital.com",
                    specialty="Orthopedics",
                    status="off-duty",
                    department_id=5,
                ),
                Doctor(
                    first_name="Lisa",
                    last_name="Anderson",
                    email="landerson@hospital.com",
                    specialty="Radiology",
                    status="available",
                    department_id=6,
                ),
            ]
            db.session.add_all(doctors)
            db.session.commit()


# ==================== HELPER FUNCTIONS ====================


def get_department_status():
    departments = Department.query.all()
    status = []
    for dept in departments:
        waiting = QueueEntry.query.filter_by(
            department_id=dept.id, status="waiting"
        ).count()
        in_progress = QueueEntry.query.filter_by(
            department_id=dept.id, status="in-progress"
        ).count()
        available_doctors = Doctor.query.filter_by(
            department_id=dept.id, status="available"
        ).count()

        queue_length = waiting + in_progress
        utilization = (
            round((queue_length / dept.capacity * 100), 1) if dept.capacity > 0 else 0
        )

        status.append(
            {
                "id": dept.id,
                "name": dept.name,
                "code": dept.code,
                "capacity": dept.capacity,
                "current_patients": queue_length,
                "waiting": waiting,
                "in_progress": in_progress,
                "available_doctors": available_doctors,
                "queue_length": queue_length,
                "utilization": utilization,
            }
        )
    return status


def get_emergency_alerts():
    alerts = []

    # Check for overloaded departments
    for dept in Department.query.all():
        queue = QueueEntry.query.filter_by(
            department_id=dept.id, status="waiting"
        ).count()
        if queue > 10:
            alerts.append(
                {
                    "type": "warning",
                    "message": f"{dept.name} has {queue} patients waiting",
                    "department": dept.name,
                }
            )

    # Check for critical patients
    critical = Patient.query.filter_by(priority=1, status="active").count()
    if critical > 0:
        alerts.append(
            {
                "type": "critical",
                "message": f"{critical} critical patients require immediate attention",
                "department": "Emergency",
            }
        )

    return alerts


# ==================== HTML ROUTES ====================


@app.route("/")
def dashboard():
    stats = {
        "total_patients": Patient.query.count(),
        "active_patients": Patient.query.filter_by(status="active").count(),
        "emergency_patients": Patient.query.filter_by(
            priority=1, status="active"
        ).count(),
        "total_doctors": Doctor.query.count(),
        "available_doctors": Doctor.query.filter_by(status="available").count(),
        "busy_doctors": Doctor.query.filter_by(status="busy").count(),
        "total_appointments_today": Appointment.query.filter(
            db.func.date(Appointment.appointment_date) == datetime.now().date()
        ).count(),
        "waiting_queue": QueueEntry.query.filter_by(status="waiting").count(),
        "pending_bills": Bill.query.filter_by(status="pending").count(),
    }

    department_status = get_department_status()
    emergency_alerts = get_emergency_alerts()

    return render_template(
        "dashboard.html",
        stats=stats,
        departments=department_status,
        alerts=emergency_alerts,
        now=datetime.now(),
    )


@app.route("/patients")
def patients():
    page = request.args.get("page", 1, type=int)
    per_page = 20
    search = request.args.get("search", "")
    status_filter = request.args.get("status", "")

    query = Patient.query
    if search:
        query = query.filter(
            db.or_(
                Patient.first_name.contains(search),
                Patient.last_name.contains(search),
                Patient.email.contains(search),
                Patient.phone.contains(search),
            )
        )
    if status_filter:
        query = query.filter_by(status=status_filter)

    patients = query.order_by(Patient.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return render_template(
        "patients.html", patients=patients, search=search, status_filter=status_filter
    )


@app.route("/doctors")
def doctors():
    page = request.args.get("page", 1, type=int)
    per_page = 20

    doctors = Doctor.query.order_by(Doctor.last_name).paginate(
        page=page, per_page=per_page, error_out=False
    )
    departments = Department.query.all()

    return render_template("doctors.html", doctors=doctors, departments=departments)


@app.route("/departments")
def departments():
    departments = Department.query.all()
    status = get_department_status()
    return render_template("departments.html", departments=departments, status=status)


@app.route("/appointments")
def appointments():
    page = request.args.get("page", 1, type=int)
    per_page = 20

    appointments = Appointment.query.order_by(
        Appointment.appointment_date.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)

    patients = Patient.query.all()
    doctors = Doctor.query.all()

    return render_template(
        "appointments.html",
        appointments=appointments,
        patients=patients,
        doctors=doctors,
    )


@app.route("/checkin")
def checkin():
    patients = Patient.query.all()  # Get all patients, not just active
    departments = Department.query.all()
    return render_template("checkin.html", patients=patients, departments=departments)


@app.route("/examination")
def examination():
    doctor_id = request.args.get("doctor_id", type=int)

    if doctor_id:
        doctor = Doctor.query.get_or_404(doctor_id)
        queue = (
            QueueEntry.query.filter_by(
                status="waiting", department_id=doctor.department_id
            )
            .order_by(QueueEntry.priority, QueueEntry.checked_in_at)
            .all()
        )
    else:
        doctor = None
        queue = (
            QueueEntry.query.filter_by(status="waiting")
            .order_by(QueueEntry.priority, QueueEntry.checked_in_at)
            .all()
        )

    doctors = Doctor.query.all()
    return render_template(
        "examination.html", queue=queue, doctor=doctor, doctors=doctors
    )


@app.route("/billing")
def billing():
    page = request.args.get("page", 1, type=int)
    per_page = 20
    status_filter = request.args.get("status", "")

    query = Bill.query
    if status_filter:
        query = query.filter_by(status=status_filter)

    bills = query.order_by(Bill.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    patients = Patient.query.all()
    total_revenue = (
        db.session.query(db.func.sum(Bill.amount)).filter_by(status="paid").scalar()
        or 0
    )
    total_pending = (
        db.session.query(db.func.sum(Bill.amount)).filter_by(status="pending").scalar()
        or 0
    )

    return render_template(
        "billing.html",
        bills=bills,
        patients=patients,
        total_revenue=total_revenue,
        total_pending=total_pending,
    )


@app.route("/reports")
def reports():
    # Get data for charts
    dept_data = []
    for dept in Department.query.all():
        count = (
            Patient.query.filter_by(status="active")
            .join(QueueEntry, QueueEntry.patient_id == Patient.id)
            .filter(QueueEntry.department_id == dept.id)
            .count()
        )
        dept_data.append({"name": dept.name, "count": count})

    # Daily appointments for last 7 days
    daily_appointments = []
    for i in range(6, -1, -1):
        date = datetime.now().date() - timedelta(days=i)
        count = Appointment.query.filter(
            db.func.date(Appointment.appointment_date) == date
        ).count()
        daily_appointments.append({"date": date.strftime("%Y-%m-%d"), "count": count})

    # Revenue by department
    revenue_data = []
    for dept in Department.query.all():
        total = (
            db.session.query(db.func.sum(Bill.amount))
            .join(Patient, Patient.id == Bill.patient_id)
            .join(QueueEntry, QueueEntry.patient_id == Patient.id)
            .filter(QueueEntry.department_id == dept.id)
            .scalar()
            or 0
        )
        revenue_data.append({"name": dept.name, "revenue": float(total)})

    return render_template(
        "reports.html",
        dept_data=dept_data,
        daily_appointments=daily_appointments,
        revenue_data=revenue_data,
    )


# ==================== API ROUTES ====================


@app.route("/api/dashboard/status")
def api_dashboard_status():
    return jsonify(
        {
            "stats": {
                "total_patients": Patient.query.count(),
                "active_patients": Patient.query.filter_by(status="active").count(),
                "emergency_patients": Patient.query.filter_by(
                    priority=1, status="active"
                ).count(),
                "total_doctors": Doctor.query.count(),
                "available_doctors": Doctor.query.filter_by(status="available").count(),
                "busy_doctors": Doctor.query.filter_by(status="busy").count(),
                "waiting_queue": QueueEntry.query.filter_by(status="waiting").count(),
            },
            "departments": get_department_status(),
            "alerts": get_emergency_alerts(),
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


@app.route("/api/patients", methods=["GET", "POST"])
def api_patients():
    if request.method == "GET":
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)

        patients = Patient.query.order_by(Patient.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return jsonify(
            {
                "patients": [p.to_dict() for p in patients.items],
                "total": patients.total,
                "pages": patients.pages,
                "current_page": page,
            }
        )

    elif request.method == "POST":
        data = request.get_json()

        patient = Patient(
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            email=data.get("email"),
            phone=data.get("phone"),
            date_of_birth=datetime.strptime(
                data.get("date_of_birth"), "%Y-%m-%d"
            ).date()
            if data.get("date_of_birth")
            else None,
            gender=data.get("gender"),
            address=data.get("address"),
            emergency_contact=data.get("emergency_contact"),
            blood_type=data.get("blood_type"),
            allergies=data.get("allergies"),
            medical_history=data.get("medical_history"),
            priority=data.get("priority", 3),
        )

        db.session.add(patient)
        db.session.commit()

        return jsonify(patient.to_dict()), 201


@app.route("/api/patients/<int:id>", methods=["GET", "PUT", "DELETE"])
def api_patient(id):
    patient = Patient.query.get_or_404(id)

    if request.method == "GET":
        return jsonify(patient.to_dict())

    elif request.method == "PUT":
        data = request.get_json()

        patient.first_name = data.get("first_name", patient.first_name)
        patient.last_name = data.get("last_name", patient.last_name)
        patient.email = data.get("email", patient.email)
        patient.phone = data.get("phone", patient.phone)
        patient.gender = data.get("gender", patient.gender)
        patient.address = data.get("address", patient.address)
        patient.emergency_contact = data.get(
            "emergency_contact", patient.emergency_contact
        )
        patient.blood_type = data.get("blood_type", patient.blood_type)
        patient.allergies = data.get("allergies", patient.allergies)
        patient.medical_history = data.get("medical_history", patient.medical_history)
        patient.status = data.get("status", patient.status)
        patient.priority = data.get("priority", patient.priority)

        db.session.commit()
        return jsonify(patient.to_dict())

    elif request.method == "DELETE":
        db.session.delete(patient)
        db.session.commit()
        return "", 204


@app.route("/api/doctors", methods=["GET", "POST"])
def api_doctors():
    if request.method == "GET":
        doctors = Doctor.query.all()
        return jsonify([d.to_dict() for d in doctors])

    elif request.method == "POST":
        data = request.get_json()

        doctor = Doctor(
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            email=data.get("email"),
            phone=data.get("phone"),
            specialty=data.get("specialty"),
            department_id=data.get("department_id"),
            status=data.get("status", "available"),
        )

        db.session.add(doctor)
        db.session.commit()

        return jsonify(doctor.to_dict()), 201


@app.route("/api/doctors/<int:id>", methods=["GET", "PUT", "DELETE"])
def api_doctor(id):
    doctor = Doctor.query.get_or_404(id)

    if request.method == "GET":
        return jsonify(doctor.to_dict())

    elif request.method == "PUT":
        data = request.get_json()

        doctor.first_name = data.get("first_name", doctor.first_name)
        doctor.last_name = data.get("last_name", doctor.last_name)
        doctor.email = data.get("email", doctor.email)
        doctor.phone = data.get("phone", doctor.phone)
        doctor.specialty = data.get("specialty", doctor.specialty)
        doctor.department_id = data.get("department_id", doctor.department_id)
        doctor.status = data.get("status", doctor.status)

        db.session.commit()
        return jsonify(doctor.to_dict())

    elif request.method == "DELETE":
        db.session.delete(doctor)
        db.session.commit()
        return "", 204


@app.route("/api/departments/status")
def api_departments_status():
    return jsonify(get_department_status())


@app.route("/api/appointments", methods=["GET", "POST"])
def api_appointments():
    if request.method == "GET":
        appointments = Appointment.query.order_by(
            Appointment.appointment_date.desc()
        ).all()
        return jsonify([a.to_dict() for a in appointments])

    elif request.method == "POST":
        data = request.get_json()

        appointment = Appointment(
            patient_id=data.get("patient_id"),
            doctor_id=data.get("doctor_id"),
            appointment_date=datetime.strptime(
                data.get("appointment_date"), "%Y-%m-%dT%H:%M"
            ),
            duration=data.get("duration", 30),
            type=data.get("type", "consultation"),
            notes=data.get("notes"),
        )

        db.session.add(appointment)
        db.session.commit()

        return jsonify(appointment.to_dict()), 201


@app.route("/api/appointments/<int:id>", methods=["GET", "PUT", "DELETE"])
def api_appointment(id):
    appointment = Appointment.query.get_or_404(id)

    if request.method == "GET":
        return jsonify(appointment.to_dict())

    elif request.method == "PUT":
        data = request.get_json()

        appointment.status = data.get("status", appointment.status)
        appointment.notes = data.get("notes", appointment.notes)

        db.session.commit()
        return jsonify(appointment.to_dict())

    elif request.method == "DELETE":
        appointment.status = "cancelled"
        db.session.commit()
        return jsonify(appointment.to_dict())


@app.route("/api/checkin", methods=["POST"])
def api_checkin():
    data = request.get_json()

    queue_entry = QueueEntry(
        patient_id=data.get("patient_id"),
        department_id=data.get("department_id"),
        priority=data.get("priority", 3),
        status="waiting",
    )

    # Update patient status
    patient = Patient.query.get(data.get("patient_id"))
    if patient:
        patient.priority = data.get("priority", patient.priority)

    db.session.add(queue_entry)
    db.session.commit()

    return jsonify(queue_entry.to_dict()), 201


@app.route("/api/examine", methods=["POST"])
def api_examine():
    data = request.get_json()

    queue_id = data.get("queue_id")
    doctor_id = data.get("doctor_id")

    queue_entry = QueueEntry.query.get_or_404(queue_id)
    doctor = Doctor.query.get_or_404(doctor_id)

    queue_entry.status = "in-progress"
    queue_entry.started_at = datetime.utcnow()

    doctor.status = "busy"

    db.session.commit()

    return jsonify({"queue_entry": queue_entry.to_dict(), "doctor": doctor.to_dict()})


@app.route("/api/queue/<int:id>/complete", methods=["POST"])
def api_complete_examination(id):
    queue_entry = QueueEntry.query.get_or_404(id)

    queue_entry.status = "completed"
    queue_entry.completed_at = datetime.utcnow()

    # Free up the doctor
    # Find the doctor who was examining this patient
    doctor = Doctor.query.get(request.json.get("doctor_id"))
    if doctor:
        doctor.status = "available"

    db.session.commit()

    return jsonify(queue_entry.to_dict())


@app.route("/api/billing/<int:patient_id>")
def api_billing(patient_id):
    bills = (
        Bill.query.filter_by(patient_id=patient_id)
        .order_by(Bill.created_at.desc())
        .all()
    )
    total = (
        db.session.query(db.func.sum(Bill.amount))
        .filter_by(patient_id=patient_id)
        .scalar()
        or 0
    )

    return jsonify({"bills": [b.to_dict() for b in bills], "total": float(total)})


@app.route("/api/bills", methods=["POST"])
def api_create_bill():
    data = request.get_json()

    # Validate required fields
    if not data.get("patient_id"):
        return jsonify({"error": "Patient is required"}), 400

    amount = data.get("amount")
    if not amount or amount == "":
        return jsonify({"error": "Amount is required"}), 400

    try:
        amount = float(amount)
        if amount <= 0:
            return jsonify({"error": "Amount must be greater than 0"}), 400
    except ValueError:
        return jsonify({"error": "Invalid amount"}), 400

    bill = Bill(
        patient_id=int(data.get("patient_id")),
        amount=amount,
        description=data.get("description", ""),
        status="pending",
    )

    db.session.add(bill)
    db.session.commit()

    return jsonify(bill.to_dict()), 201


@app.route("/api/bills/<int:id>/pay", methods=["POST"])
def api_pay_bill(id):
    bill = Bill.query.get_or_404(id)

    bill.status = "paid"
    bill.paid_at = datetime.utcnow()

    db.session.commit()

    return jsonify(bill.to_dict())


@app.route("/api/reports/daily")
def api_daily_reports():
    days = request.args.get("days", 7, type=int)

    data = []
    for i in range(days - 1, -1, -1):
        date = datetime.now().date() - timedelta(days=i)

        appointments = Appointment.query.filter(
            db.func.date(Appointment.appointment_date) == date
        ).count()

        revenue = (
            db.session.query(db.func.sum(Bill.amount))
            .filter(db.func.date(Bill.created_at) == date, Bill.status == "paid")
            .scalar()
            or 0
        )

        data.append(
            {
                "date": date.strftime("%Y-%m-%d"),
                "appointments": appointments,
                "revenue": float(revenue),
            }
        )

    return jsonify(data)


@app.route("/api/reports/departments")
def api_department_reports():
    data = []
    for dept in Department.query.all():
        patients = (
            Patient.query.filter_by(status="active")
            .join(QueueEntry, QueueEntry.patient_id == Patient.id)
            .filter(QueueEntry.department_id == dept.id)
            .count()
        )

        revenue = (
            db.session.query(db.func.sum(Bill.amount))
            .join(Patient, Patient.id == Bill.patient_id)
            .join(QueueEntry, QueueEntry.patient_id == Patient.id)
            .filter(QueueEntry.department_id == dept.id)
            .scalar()
            or 0
        )

        avg_wait = (
            db.session.query(
                db.func.avg(
                    db.func.strftime("%s", QueueEntry.started_at)
                    - db.func.strftime("%s", QueueEntry.checked_in_at)
                )
            )
            .filter(
                QueueEntry.department_id == dept.id, QueueEntry.started_at.isnot(None)
            )
            .scalar()
            or 0
        )

        data.append(
            {
                "department": dept.name,
                "patients": patients,
                "revenue": float(revenue),
                "avg_wait_time": round(float(avg_wait) / 60, 1),  # Convert to minutes
            }
        )

    return jsonify(data)


# ==================== EXPORT ROUTES ====================


@app.route("/api/patients/export/csv")
def export_patients_csv():
    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "ID",
            "First Name",
            "Last Name",
            "Email",
            "Phone",
            "Date of Birth",
            "Gender",
            "Status",
            "Priority",
            "Created At",
        ]
    )

    for patient in Patient.query.all():
        writer.writerow(
            [
                patient.id,
                patient.first_name,
                patient.last_name,
                patient.email,
                patient.phone,
                patient.date_of_birth,
                patient.gender,
                patient.status,
                patient.priority,
                patient.created_at,
            ]
        )

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=patients.csv"},
    )


# ==================== ERROR HANDLERS ====================


@app.errorhandler(404)
def not_found(error):
    if request.is_json or request.path.startswith("/api/"):
        return jsonify({"error": "Not found"}), 404
    return render_template("base.html", error="Page not found"), 404


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    if request.is_json or request.path.startswith("/api/"):
        return jsonify({"error": "Internal server error"}), 500
    return render_template("base.html", error="Internal server error"), 500


# ==================== MAIN ====================

# Initialize database on startup (works for both direct run and gunicorn)
init_db()

if __name__ == "__main__":
    # Production: use PORT env var; Development: default 5000
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    app.run(debug=debug_mode, host="0.0.0.0", port=port)
