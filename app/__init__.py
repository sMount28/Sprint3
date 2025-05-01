# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

# Import core packages
import os

# Import Flask 
from flask import Flask

# Inject Flask magic
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'  # Create a folder named 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
app.secret_key = "jhfskjlwelkj"

# Import routing to render the pages
from app import views

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
