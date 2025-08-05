import os
from flask import Flask
from flask_restful import Api
from flask_migrate import Migrate
from database import engine  # Import to ensure database is initialized
from models import Base

from routes.experts import ExpertResource, ExpertListResource
from routes.experiences import ExperienceResource, ExperienceListResource
from routes.attributes import AttributeResource, AttributeListResource

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://postgres:cerca123@uf-cerca-v1.cluster-cxgooo0scwa0.us-east-1.rds.amazonaws.com/cerca')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Create a mock db object for Flask-Migrate
class MockDB:
    def __init__(self):
        self.Model = Base
        self.metadata = Base.metadata
        self.engine = engine
        
    def get_engine(self):
        return self.engine
        
db = MockDB()
migrate = Migrate(app, db)
api = Api(app)

api.add_resource(ExpertListResource, '/api/experts')
api.add_resource(ExpertResource, '/api/experts/<int:expert_id>')

api.add_resource(ExperienceListResource, '/api/experiences')
api.add_resource(ExperienceResource, '/api/experiences/<int:experience_id>')

api.add_resource(AttributeListResource, '/api/attributes')
api.add_resource(AttributeResource, '/api/attributes/<int:attribute_id>')

@app.route("/")
def hello_world():
    return "<p>Cerca Expert Search API</p>"

@app.route("/health")
def health_check():
    return {"status": "healthy", "service": "cerca-api"}

if __name__ == '__main__':
    # Use environment variables for production configuration
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    
    # Ensure unbuffered output for debugging
    import sys
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
    
    app.run(host=host, port=port, debug=debug)