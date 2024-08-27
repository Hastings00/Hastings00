from flask import Flask, request, render_template, redirect, url_for, flash, send_file
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from fpdf import FPDF
import pandas as pd
import pickle
import PyPDF2
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'uploads/'
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'pdf'}
users = {"teacher": generate_password_hash("password123")}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def authenticate(username, password):
    return username in users and check_password_hash(users[username], password)

def read_pdf(file_path):
    text = ""
    with open(file_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text()
    return text

def load_data(file_path):
    if file_path.endswith('.csv'):
        return pd.read_csv(file_path)
    elif file_path.endswith('.xlsx'):
        return pd.read_excel(file_path)
    elif file_path.endswith('.pdf'):
        pdf_text = read_pdf(file_path)
        return pd.read_csv(pd.compat.StringIO(pdf_text))
    else:
        raise ValueError("Unsupported file format")

def train_model(data, label_column):
    X = data.drop(label_column, axis=1)
    y = data[label_column]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
    model = RandomForestClassifier()
    model.fit(X_train, y_train)
    accuracy = accuracy_score(y_test, model.predict(X_test))
    with open('model.pkl', 'wb') as file:
        pickle.dump(model, file)
    return accuracy

def generate_report_card(data, student_number, school_name, class_name, logo_path):
    pdf = FPDF()
    pdf.add_page()
    pdf.image(logo_path, x=10, y=8, w=30)
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Report Card for {school_name} - {class_name}", ln=True, align='C')
    student_data = data[data['Student Number'] == int(student_number)]
    for index, row in student_data.iterrows():
        pdf.cell(200, 10, txt=f"Name: {row['Name']} | Grade: {row['Grade']}", ln=True)
    pdf.output(f"report_card_student_{student_number}.pdf")

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if authenticate(username, password):
            return redirect(url_for('upload'))
        flash('Invalid credentials.')
    return render_template('index.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '' or not allowed_file(file.filename):
            flash('No selected file or unsupported file type')
            return redirect(request.url)
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        data = load_data(file_path)
        return redirect(url_for('generate_report', filename=filename))
    return render_template('upload.html')

@app.route('/generate_report/<filename>', methods=['GET', 'POST'])
def generate_report(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    data = load_data(file_path)
    if request.method == 'POST':
        student_number = request.form['student_number']
        school_name = request.form['school_name']
        class_name = request.form['class_name']
        logo_path = os.path.join(app.config['UPLOAD_FOLDER'], 'logo.jpg')  # Adjust path if necessary
        generate_report_card(data, student_number, school_name, class_name, logo_path)
        return send_file(f"report_card_student_{student_number}.pdf", as_attachment=True)
    return render_template('report.html')

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)
