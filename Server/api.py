from spider import Spider
from flask import Flask, request, render_template, jsonify

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False


@app.route("/", methods=["GET", "POST"])
def index():

    post_format = {"username": "", "password": ""}

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = Spider(username, password)
        user.login()
        if user.login_status:
            info = user.modify_data()
            return jsonify(info)
        else:
            return "登录失败"

    else:
        return render_template("index.html", format=post_format)


if __name__ == "__main__":

    from werkzeug.contrib.fixers import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app)

    app.run("0.0.0.0")

