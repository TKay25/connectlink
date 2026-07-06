import sys
sys.path.insert(0, '.')
from flask import Flask, render_template
app = Flask(__name__, template_folder='templates', static_folder='static', static_url_path='/static')
app.jinja_env.auto_reload = True

@app.route('/')
def index():
    return render_template('mainindex.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
