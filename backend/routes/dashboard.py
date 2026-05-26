from flask import Blueprint, jsonify
from services.chart_service import get_dashboard_data

dashboard_bp = Blueprint("dashboard_bp", __name__)

@dashboard_bp.route("/dashboard", methods=["GET"])
def dashboard():
    return jsonify(get_dashboard_data()), 200