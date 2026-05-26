import os
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from config import Config
from routes.upload import upload_bp
from routes.query import query_bp
from routes.insights import insights_bp
from routes.ai import ai_bp
from routes.dashboard import dashboard_bp

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app)

    app.register_blueprint(upload_bp, url_prefix="/api")
    app.register_blueprint(query_bp, url_prefix="/api")
    app.register_blueprint(insights_bp, url_prefix="/api")
    app.register_blueprint(ai_bp, url_prefix="/api")
    app.register_blueprint(dashboard_bp, url_prefix="/api")

    @app.route("/")
    def home():
        return jsonify({"message": "AI Data Analyst Assistant API running"})

    @app.route("/dashboard")
    def dashboard_page():
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.route("/assets/<path:filename>")
    def frontend_assets(filename):
        return send_from_directory(FRONTEND_DIR, filename)

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
