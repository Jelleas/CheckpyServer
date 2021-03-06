from flask import Flask, request, redirect, url_for, jsonify
from werkzeug.utils import secure_filename
import json
import requests
import os
import re
import filemanager
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = "./uploads"
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)

        file = request.files['file']
        studentnumber = request.form["studentnumber"]

        if not studentnumber.isdigit():
            flash("studentnumber may only contain digits")
            return redirect(request.url)

        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)

        if not (file and _allowedFile(file.filename)):
            flash('Illegal file')
            return redirect(request.url)

        _save(file, studentnumber)

        filename = secure_filename(file.filename)
        return redirect(url_for("test", studentnumber = studentnumber, filename = filename))

    return _uploadHTML()

@app.route("/<studentnumber>/<filename>")
def test(studentnumber, filename):
    with open(_filepath(filename, studentnumber)) as f:
        response = requests.post("http://localhost:4000/upload", files = {'file' : f})
    return _testJsonToHTML(response.json())

@app.route("/<studentnumber>/<submission>/<filename>")
def testDropbox(studentnumber, submission, filename):
    studentnumber = secure_filename(studentnumber)
    submission = secure_filename(submission)
    filename = secure_filename(filename)
    path = "/{}/{}/{}".format(studentnumber, submission, filename)

    if filemanager.isCached(path):
        with filemanager.getCached(path) as jsonFile:
            testJson = json.loads(jsonFile.read())
    else:
        with filemanager.get(path) as f:
            response = requests.post("http://localhost:4000/upload", files = {'file' : f})
            testJson = response.json()
            filemanager.cache(json.dumps(testJson), path)

    return _testJsonToHTML(testJson)

def _allowedFile(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ['py']

def _testJsonToHTML(testJson):
    html = \
"""
<head>
    <style type=\"text/css\">
        {style}
    </style>
</head>
<body>
    <b>contents:</b> <br/>
{src}<br/>
    <b>checkpy output:</b> <br/>
{output}
</body>
"""

    output = _checkpyOutputToHTML(testJson["output"])
    source = highlight(testJson["source"], PythonLexer(), HtmlFormatter(linenos=True, style='monokai'))
    style = HtmlFormatter().get_style_defs('.highlight')

    return html.format(src = source, output = output, style = style)

def _checkpyOutputToHTML(checkpyOutput):
    colors = {"\x1b[96m" : "#1E90FF", "\x1b[92m" : "#008000", "\x1b[91m" : "#DC143C", "\x1b[93m" : "#fda700"}
    ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
    output = ""
    for line in checkpyOutput:
        color = "black"
        for ansi_seq in colors:
            if ansi_seq in line:
                color = colors[ansi_seq]
        output += "<div style = \"color:{};\"> {} </div>\n".format(color, ansi_escape.sub('', line))
    return output

def _uploadHTML():
    html = '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form method=post enctype=multipart/form-data>
      <p><input type=file name=file>
         studentnumber: <input type=text name=studentnumber>
         <input type=submit value=Upload>
    </form>
    '''
    return html

def _filepath(filename, studentnumber):
    destDir = os.path.join(app.config['UPLOAD_FOLDER'], studentnumber)
    return os.path.join(destDir, filename)

def _save(file, studentnumber):
    filename = secure_filename(file.filename)
    studentnumber = secure_filename(str(studentnumber))
    destDir = os.path.join(app.config['UPLOAD_FOLDER'], studentnumber)
    if not os.path.exists(destDir):
        os.makedirs(destDir)
    file.save(os.path.join(destDir, filename))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80)
