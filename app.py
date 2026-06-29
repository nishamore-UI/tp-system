from dotenv import load_dotenv
import os
from flask import Flask
from extensions import db
from routes import routes
from models import Admin


load_dotenv()

app = Flask(__name__)

app.secret_key = "supersecretkey"

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")

app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_recycle": 300
}

db.init_app(app)

app.register_blueprint(routes)

with app.app_context():
    db.create_all()

    from models import Admin

    admin = Admin.query.filter_by(username="admin").first()

    if admin:
        admin.role = "admin"
    else:
        admin = Admin(username="admin", password="admin123", role="admin")
        db.session.add(admin)

    if not Admin.query.filter_by(username="staff").first():
        staff = Admin(username="staff", password="staff123", role="staff")
        db.session.add(staff)

    db.session.commit()

if __name__ == "__main__":
    app.run(debug=True, port=5001)
