import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from flask import Flask, send_from_directory
from flask_restful import Api
from flask_migrate import Migrate
from database import engine  # Import to ensure database is initialized
from models import Base

from routes.Experts import ExpertResource, ExpertListResource
from routes.experiences import ExperienceResource, ExperienceListResource
from routes.attributes import AttributeResource, AttributeListResource
from routes.search import ExpertSearchResource
from routes.prompts import PromptResource, PromptListResource, PromptByNameResource, PromptVersionActivateResource
from routes.solicitation_roles import SolicitationRolesListResource, SolicitationRoleResource

app = Flask(__name__)

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

api.add_resource(ExpertSearchResource, '/api/experts/search')

api.add_resource(PromptListResource, '/api/prompts')
api.add_resource(PromptResource, '/api/prompts/<int:prompt_id>')
api.add_resource(PromptVersionActivateResource, '/api/prompts/<int:prompt_id>/activate')
api.add_resource(PromptByNameResource, '/api/prompts/by-name/<string:template_name>')

api.add_resource(SolicitationRolesListResource, '/api/solicitation-roles')
api.add_resource(SolicitationRoleResource, '/api/solicitation-roles/<string:role_id>')

@app.route("/")
def hello_world():
    return "<p>Cerca Expert Search API</p>"

@app.route("/health")
def health_check():
    return {"status": "healthy", "service": "cerca-api"}

@app.route("/ui/experts")
def experts_list_ui():
    return send_from_directory('static', 'experts.html')

@app.route("/ui/prompts")
def prompts_ui():
    return send_from_directory('static', 'prompts.html')


@app.route("/ui/search")
def search_ui():
    return send_from_directory('static', 'search.html')

@app.route("/ui/evaluations")
def evaluations_ui():
    return send_from_directory('static', 'evaluations.html')

@app.route("/ui/solicitation-roles")
def solicitation_roles_ui():
    return send_from_directory('static', 'solicitation_roles.html')

# Import evaluation routes
from routes.evaluations import evaluation_dashboard, evaluation_details, evaluation_test_cases, evaluation_api_data, evaluation_list_api

# Add evaluation routes to app
app.add_url_rule('/evaluations', 'evaluation_dashboard', evaluation_dashboard)
app.add_url_rule('/evaluations/<filename>', 'evaluation_details', evaluation_details)
app.add_url_rule('/evaluations/<filename>/test-cases', 'evaluation_test_cases', evaluation_test_cases)
app.add_url_rule('/api/evaluations/<filename>/data', 'evaluation_api_data', evaluation_api_data)
app.add_url_rule('/api/evaluations/list', 'evaluation_list_api', evaluation_list_api)

if __name__ == '__main__':
    # Use environment variables for production configuration
    port = int(os.getenv('PORT', 5001))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    
    # Ensure unbuffered output for debugging
    import sys
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
    
    app.run(host=host, port=port, debug=debug)
