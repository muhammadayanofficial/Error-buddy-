"""PatchLens AI - Flask application."""
from flask import Flask, Response, jsonify, render_template, request

import ai_service
import config
import database
from export import build_markdown


def validate_submission(data):
    """Return cleaned (code, language, error_text, mode) or raise ValueError with a clear message."""
    if not isinstance(data, dict):
        raise ValueError("Request body must be JSON.")
    code = str(data.get("code", "")).strip("\r\n")
    error_text = str(data.get("error_text", "")).strip()
    language = str(data.get("language", "Python"))
    mode = str(data.get("mode", "review"))
    if not code.strip():
        raise ValueError("Paste some code into the editor before running a review.")
    if len(code) > config.MAX_CODE_CHARS:
        raise ValueError(f"Code is too long. The limit is {config.MAX_CODE_CHARS:,} characters.")
    if len(error_text) > config.MAX_ERROR_CHARS:
        raise ValueError(f"The error message is too long. The limit is {config.MAX_ERROR_CHARS:,} characters.")
    if language not in config.LANGUAGES:
        raise ValueError("Choose a language from the list.")
    if mode not in ("review", "debug"):
        raise ValueError("Unknown review mode.")
    if mode == "debug" and not error_text:
        raise ValueError("Add an error message or traceback to use Debug error.")
    return code, language, error_text, mode


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(config.Config)
    if test_config:
        app.config.update(test_config)
    database.init_db(app.config["DATABASE"])

    @app.get("/")
    def index():
        return render_template("index.html", languages=config.LANGUAGES, max_code=config.MAX_CODE_CHARS)

    @app.get("/api/status")
    def status():
        return jsonify(ai_configured=bool(config.get_api_key()), model=config.get_model())

    @app.post("/api/review")
    def review():
        try:
            code, language, error_text, mode = validate_submission(request.get_json(silent=True))
        except ValueError as exc:
            return jsonify(error=str(exc)), 400
        try:
            result = ai_service.analyze(code, language, error_text, mode)
        except ai_service.AIConfigError as exc:
            return jsonify(error=str(exc), code="not_configured"), 503
        except ai_service.AIServiceError as exc:
            return jsonify(error=str(exc), code="ai_error"), 502
        review_id = database.save_review(app.config["DATABASE"], language, mode, code, error_text, result)
        return jsonify(id=review_id, result=result)

    @app.post("/api/local-check")
    def local_check():
        data = request.get_json(silent=True) or {}
        code = str(data.get("code", ""))
        if not code.strip():
            return jsonify(error="Paste some code before running a local check."), 400
        return jsonify(ai_service.local_check(code, str(data.get("language", ""))))

    @app.get("/api/reviews")
    def list_reviews():
        return jsonify(reviews=database.list_reviews(app.config["DATABASE"]))

    @app.get("/api/reviews/<int:review_id>")
    def get_review(review_id):
        item = database.get_review(app.config["DATABASE"], review_id)
        return (jsonify(item), 200) if item else (jsonify(error="That review no longer exists."), 404)

    @app.delete("/api/reviews/<int:review_id>")
    def delete_review(review_id):
        if database.delete_review(app.config["DATABASE"], review_id):
            return jsonify(deleted=True)
        return jsonify(error="That review no longer exists."), 404

    @app.get("/api/reviews/<int:review_id>/export")
    def export_review(review_id):
        item = database.get_review(app.config["DATABASE"], review_id)
        if not item:
            return jsonify(error="That review no longer exists."), 404
        return Response(build_markdown(item), mimetype="text/markdown",
                        headers={"Content-Disposition": f'attachment; filename="patchlens-review-{review_id}.md"'})

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
