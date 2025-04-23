# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

# Import core packages
import os

# Import Flask 
from flask import Flask
import pymysql

# Inject Flask magic
app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = 'uploads'  # Create a folder named 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = pymysql.connect(
        host='35.245.249.29',
        port=3306,
        user='admin',
        password='SMUGroup3',
        charset="utf8mb4",
        database='PeerEvaluationDB',
        cursorclass=pymysql.cursors.DictCursor
    )
cursor = db.cursor()
app.config["SQLALCHEMY_POOL_RECYCLE"] = 3600


# Import routing to render the pages
from app import views

app.secret_key = "jhfskjlwelkj"




if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
