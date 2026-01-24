import os
from flask import Flask, request, redirect, url_for, send_from_directory, flash, render_template_string
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.utils import secure_filename

# -------------------------
# Configuration
# -------------------------
app = Flask(__name__)
app.secret_key = "smart-india-hackathon-secret"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(BASE_DIR, 'documents.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'}

db = SQLAlchemy(app)

# -------------------------
# Database Model
# -------------------------
class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(300), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)

# -------------------------
# Utility
# -------------------------
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# -------------------------
# Routes
# -------------------------
@app.route("/")
def index():
    documents = Document.query.order_by(Document.upload_date.desc()).all()
    return render_template_string(INDEX_TEMPLATE, documents=documents)

@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        file = request.files.get("file")
        department = request.form.get("department")
        category = request.form.get("category")

        if not file or file.filename == "":
            flash("No file selected")
            return redirect(request.url)

        if file and allowed_file(file.filename):
            if not os.path.exists(UPLOAD_FOLDER):
                os.makedirs(UPLOAD_FOLDER)

            filename = secure_filename(file.filename)
            file.save(os.path.join(UPLOAD_FOLDER, filename))

            new_doc = Document(filename=filename, department=department, category=category)
            db.session.add(new_doc)
            db.session.commit()

            flash("File uploaded successfully!")
            return redirect(url_for("index"))
        else:
            flash("Invalid file type. Allowed: pdf, doc, docx, jpg, png")
            return redirect(request.url)

    return render_template_string(UPLOAD_TEMPLATE)

@app.route("/download/<int:doc_id>")
def download(doc_id):
    doc = Document.query.get_or_404(doc_id)
    return send_from_directory(app.config["UPLOAD_FOLDER"], doc.filename, as_attachment=True)

@app.route("/delete/<int:doc_id>")
def delete(doc_id):
    doc = Document.query.get_or_404(doc_id)
    try:
        os.remove(os.path.join(app.config["UPLOAD_FOLDER"], doc.filename))
    except FileNotFoundError:
        pass
    db.session.delete(doc)
    db.session.commit()
    flash("File deleted successfully!")
    return redirect(url_for("index"))

# -------------------------
# Inline Templates
# -------------------------
LAYOUT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>KMRL Document Manager</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="{{ url_for('index') }}">KMRL DMS</a>
            <div class="ms-auto">
                <a class="btn btn-light btn-sm" href="{{ url_for('upload') }}">Upload Document</a>
            </div>
        </div>
    </nav>
    <div class="container mt-4">
        {% with messages = get_flashed_messages() %}
            {% if messages %}
                {% for msg in messages %}
                    <div class="alert alert-info">{{ msg }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        {% block content %}{% endblock %}
    </div>
</body>
</html>
"""

INDEX_TEMPLATE = (
    "{% extends none %}" + LAYOUT_TEMPLATE +
    "{% block content %}"
    "<h2 class='mb-3'>All Documents</h2>"
    "<table class='table table-bordered table-striped'>"
    "<thead class='table-dark'>"
    "<tr><th>ID</th><th>Filename</th><th>Department</th><th>Category</th><th>Uploaded On</th><th>Actions</th></tr>"
    "</thead><tbody>"
    "{% for doc in documents %}"
    "<tr>"
    "<td>{{ doc.id }}</td>"
    "<td>{{ doc.filename }}</td>"
    "<td>{{ doc.department }}</td>"
    "<td>{{ doc.category }}</td>"
    "<td>{{ doc.upload_date.strftime('%d-%m-%Y %H:%M') }}</td>"
    "<td>"
    "<a class='btn btn-sm btn-success' href='{{ url_for('download', doc_id=doc.id) }}'>Download</a> "
    "<a class='btn btn-sm btn-danger' href='{{ url_for('delete', doc_id=doc.id) }}'>Delete</a>"
    "</td>"
    "</tr>"
    "{% endfor %}"
    "</tbody></table>"
    "{% endblock %}"
)

UPLOAD_TEMPLATE = (
    "{% extends none %}" + LAYOUT_TEMPLATE +
    "{% block content %}"
    "<h2>Upload Document</h2>"
    "<form method='POST' enctype='multipart/form-data'>"
    "<div class='mb-3'>"
    "<label class='form-label'>Select File</label>"
    "<input type='file' name='file' class='form-control' required>"
    "</div>"
    "<div class='mb-3'>"
    "<label class='form-label'>Department</label>"
    "<input type='text' name='department' class='form-control' placeholder='e.g. HR, Procurement' required>"
    "</div>"
    "<div class='mb-3'>"
    "<label class='form-label'>Category</label>"
    "<input type='text' name='category' class='form-control' placeholder='e.g. Invoice, Report' required>"
    "</div>"
    "<button type='submit' class='btn btn-primary'>Upload</button>"
    "</form>"
    "{% endblock %}"
)

# -------------------------
# Run
# -------------------------
if __name__ == "__main__":
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    with app.app_context():
        db.create_all()
    # host=127.0.0.1 works with VS Code debugger
    app.run(debug=True, host="127.0.0.1", port=5000)