import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from src.config import config
from src.models import db
from src.routes.user import user_bp

def create_app(config_name=None):
    """Application factory pattern"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}} )
    jwt = JWTManager(app)
    
    # Register blueprints
    app.register_blueprint(user_bp, url_prefix='/api')
    
    # Import and register other blueprints
    from src.routes.course import course_bp
    app.register_blueprint(course_bp, url_prefix="/api")
    from src.routes.content import content_bp
    app.register_blueprint(content_bp, url_prefix="/api")
    from src.routes.progress import progress_bp
    app.register_blueprint(progress_bp, url_prefix="/api")
    from src.routes.assessment import assessment_bp
    app.register_blueprint(assessment_bp, url_prefix="/api")
    from src.routes.communication import communication_bp
    app.register_blueprint(communication_bp, url_prefix="/api")
    from src.routes.analytics import analytics_bp
    app.register_blueprint(analytics_bp, url_prefix="/api")
    
    # Create database tables
    with app.app_context():
        db.create_all()  # 테이블 먼저 생성
        
        # Create default roles if they don't exist
        from src.models import Role
        default_roles = [
            {'name': 'student', 'description': '학생'},
            {'name': 'instructor', 'description': '교수'},
            {'name': 'teaching_assistant', 'description': '조교'},
            {'name': 'admin', 'description': '관리자'}
        ]
        
        for role_data in default_roles:
            existing_role = Role.query.filter_by(name=role_data['name']).first()
            if not existing_role:
                role = Role(**role_data)
                db.session.add(role)
        
        db.session.commit()
    
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve(path):
        static_folder_path = app.static_folder
        if static_folder_path is None:
            return "Static folder not configured", 404

        if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
            return send_from_directory(static_folder_path, path)
        else:
            index_path = os.path.join(static_folder_path, 'index.html')
            if os.path.exists(index_path):
                return send_from_directory(static_folder_path, 'index.html')
            else:
                return "index.html not found", 404
    
    @app.route('/api/health')
    def health_check():
        return {'status': 'healthy', 'message': 'LMS API is running'}
    
    return app

app = create_app()

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5004, debug=True)