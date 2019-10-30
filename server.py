from flask import Flask, render_template, request
from mapathon_count import main2
import threading

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def form():
    return render_template('fileuploadform.html')

@app.route('/calculate', methods=['GET', 'POST'])
def calculate():
    if request.method == 'POST':
        f = request.files['file']
        usernames = f.read().split('\r\n')

    # Get content of request
    email = request.form['email']
    daterange = request.form['daterange'].split('-')
    print(daterange)
    print(type(daterange))

    x = threading.Thread(target=main2, args=(usernames,daterange,email))
    x.start()
    # Do calculations and shit
    return render_template('success.html',email=request.form['email'])

if __name__ == "__main__":
    app.run(host='0.0.0.0',port=3000,debug=True)