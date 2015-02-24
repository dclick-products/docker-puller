from flask import Flask
from flask import request
from flask import jsonify
from flask import Response
import json
import subprocess
import sys
import getopt
import sqlite3
import os

app = Flask(__name__)
config = None
con = None
token = None

def root_dir():  # pragma: no cover
    return os.path.abspath(os.path.dirname(__file__))


def get_file(filename):  # pragma: no cover
    try:
        src = os.path.join(root_dir(), filename)
        return open(src).read()
    except IOError as exc:
        return str(exc)


@app.route('/', methods=['GET'])
def metrics():  # pragma: no cover
    content = get_file('index.html')
    return Response(content, mimetype="text/html")

@app.route('/hook/execute', methods=['POST'])
def hook_listen():
    if request.method == 'POST':
        reqToken = request.args.get('token')
        if reqToken == token:
            hook = request.args.get('hook')
            if hook:
                cur = con.cursor()
                cur.execute('''select * from hooks_script where name=?''', (str(hook),))
                a = cur.fetchone()
                hook_value = a[1]
                if hook_value:
                    try:
                        value = os.system("echo " + hook_value + " > /tmp/script.sh")
                        if value == 0:
                            value = os.system("sh /tmp/script.sh")
                            if value == 0:
                                return jsonify(success=True), 200
                        return jsonify(success=False, error="Failed to execute hook script"), 400
                    except OSError as e:
                        return jsonify(success=False, error=str(e)), 400
                else:
                    return jsonify(success=False, error="Hook not found"), 404
            else:
                return jsonify(success=False, error="Invalid request: missing hook"), 400
        else:
            return jsonify(success=False, error="Invalid token"), 400

@app.route('/hook/<name>/script', methods=['POST'])
def add_script(name):
    if request.method == 'POST':
        script=request.form['script']
        cur = con.cursor()
        cur.execute("delete from hooks_script where name=?", (str(name),))
        cur.execute("insert into hooks_script values (?, ?)", (str(name),str(script)))
        con.commit()
        return jsonify(success=True), 200

@app.route('/hook/<name>', methods=['GET'])
def read_hook(name):
    if request.method == 'GET':
        cur = con.cursor()
        cur.execute('''select * from hooks_script where name=?''', (str(name),))
        a = cur.fetchone()
        if a is None:
            return ""
        return Response(json.dumps(a[1]), mimetype='application/json')

@app.route('/hook/<name>', methods=['DELETE'])
def delete_hook(name):
    if request.method == 'DELETE':
        cur = con.cursor()
        cur.execute('''delete from hooks_script where name=?''', (str(name),))
        cur.execute('''delete from hooks where name=?''', (str(name),))
        con.commit()
        return jsonify(success=True), 200

@app.route('/hook', methods=['GET'])
def list_hook():
    if request.method == 'GET':
        result = []
        cur = con.cursor()
        cur.execute("select * from hooks")
        all_rows = cur.fetchall()
        for row in all_rows:
            result.append(row[0])
        return Response(json.dumps(result),  mimetype='application/json')

@app.route('/hook', methods=['POST'])
def add_hook():
    if request.method == 'POST':
        hook = request.form['hook']
        cur = con.cursor()
        cur.execute("insert into hooks values (?)", (str(hook),))
        con.commit()
        return jsonify(success=True), 200

def startSQLite():
    global con
    con = sqlite3.connect("/data/puller.db", check_same_thread=False)
    cur = con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS hooks ('name' varchar(100) not null, PRIMARY KEY(name))")
    cur.execute("CREATE TABLE IF NOT EXISTS hooks_script ('name' varchar(100) not null, 'script' TEXT null, PRIMARY KEY(name))")
    con.commit()

def main(argv):
    global token
    port = 8000
    token = "sample-token"
    try:
        opts, args = getopt.getopt(argv,"hpt:",["port="])
    except getopt.GetoptError:
        print 'app.py -p port -t token'
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print 'app.py -p port'
            sys.exit()
        elif opt in ("-p", "--port"):
            port = int(arg)
        elif opt in ("-t"):
            token = str(arg)

    startSQLite()
    app.debug = True
    app.run(host="0.0.0.0", port=port)

if __name__ == '__main__':
    main(sys.argv[1:])
