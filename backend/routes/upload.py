from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
import uuid
from pathlib import Path
import pandas as pd
from utils.validator import allowed_file
from services.data_service import load_data, clean_data, basic_summary
from services.db_service import save_to_database
from services.state import set_current_data

upload_bp = Blueprint("upload_bp", __name__)

@upload_bp.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Only CSV and XLSX files allowed"}), 400

    upload_folder = Path(current_app.config["UPLOAD_FOLDER"]).resolve()
    upload_folder.mkdir(parents=True, exist_ok=True)

    # Save using a secure, unique filename to avoid overwrite and permission issues
    safe_name = secure_filename(file.filename)
    unique_name = f"{uuid.uuid4().hex}_{safe_name}"
    file_path = upload_folder / unique_name
    file.save(str(file_path))

    try:
        df = load_data(file_path)
        df = clean_data(df)
        set_current_data(df)
        save_to_database(df)

        preview = df.head(5).fillna("").to_dict(orient="records")
        summary = basic_summary(df)

        return jsonify({
            "message": "File uploaded and processed successfully",
            "filename": unique_name,
            "rows": summary["rows"],
            "columns": summary["columns"],
            "preview": preview,
            "summary": summary
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500