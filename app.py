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

@app.route("/")
def hello_world():
    return "<p>Cerca Expert Search API</p>"

@app.route("/health")
def health_check():
    return {"status": "healthy", "service": "cerca-api"}

@app.route("/ui/experts")
def experts_list_ui():
    return send_from_directory('static', 'experts.html')


@app.route("/ui/search")
def search_ui():
    return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Expert Search - Weight Testing</title>
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
            margin: 0; padding: 20px; background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px; margin: 0 auto; background: white;
            border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; padding: 20px; text-align: center; position: relative;
        }
        
        .nav-links {
            position: absolute; top: 20px; left: 20px; display: flex; gap: 15px;
        }
        
        .nav-link {
            color: rgba(255, 255, 255, 0.9); text-decoration: none; padding: 8px 16px;
            border-radius: 20px; background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px); transition: all 0.3s ease;
            font-size: 14px; font-weight: 500;
        }
        
        .nav-link:hover {
            background: rgba(255, 255, 255, 0.2); color: white; transform: translateY(-1px);
        }
        
        .nav-link.active {
            background: rgba(255, 255, 255, 0.3); color: white;
        }
        .content { padding: 20px; display: grid; grid-template-columns: 1fr 2fr; gap: 20px; }
        .controls { background: #f8f9fa; padding: 20px; border-radius: 8px; border: 1px solid #e9ecef; }
        .results { background: white; padding: 20px; border-radius: 8px; border: 1px solid #e9ecef; }
        .search-input {
            width: 100%; padding: 12px; border: 2px solid #e9ecef; border-radius: 6px;
            font-size: 16px; margin-bottom: 20px; resize: vertical; min-height: 120px;
            font-family: inherit; line-height: 1.4;
        }
        .search-input:focus { outline: none; border-color: #667eea; }
        .weight-controls { margin-bottom: 20px; }
        .weight-item {
            display: flex; align-items: center; margin-bottom: 12px; padding: 8px;
            background: white; border-radius: 6px; border: 1px solid #dee2e6;
        }
        .weight-label { flex: 1; font-weight: 500; text-transform: capitalize; }
        .weight-slider { flex: 2; margin: 0 10px; }
        .weight-value { width: 50px; text-align: center; font-weight: bold; color: #667eea; }
        .search-button {
            width: 100%; padding: 12px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; border: none; border-radius: 6px; font-size: 16px; font-weight: 500;
            cursor: pointer; transition: transform 0.2s;
        }
        .search-button:hover { transform: translateY(-1px); }
        .search-button:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }
        .expert-card {
            border: 1px solid #e9ecef; border-radius: 8px; padding: 16px;
            margin-bottom: 16px; background: #f8f9fa;
        }
        .expert-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
        .expert-name { font-size: 18px; font-weight: 600; color: #343a40; }
        .expert-score {
            background: #667eea; color: white; padding: 4px 8px;
            border-radius: 12px; font-size: 14px; font-weight: 500;
        }
        .profile-id {
            font-size: 12px; color: #6c757d; font-weight: normal;
            margin-left: 8px; font-style: italic;
        }
        .expert-summary { color: #6c757d; margin-bottom: 12px; line-height: 1.4; }
        .experiences { margin-top: 12px; }
        .experience {
            background: white; padding: 12px; border-radius: 6px;
            margin-bottom: 8px; border-left: 4px solid #667eea;
        }
        .experience-summary { font-weight: 500; margin-bottom: 4px; }
        .experience-dates { font-size: 12px; color: #6c757d; margin-bottom: 8px; }
        .attributes { display: flex; flex-wrap: wrap; gap: 6px; }
        .attribute {
            background: #e9ecef; padding: 2px 6px; border-radius: 4px;
            font-size: 11px; color: #495057;
        }
        .attribute.agency { background: #e3f2fd; color: #1565c0; }
        .attribute.role { background: #f3e5f5; color: #7b1fa2; }
        .attribute.skill { background: #e8f5e8; color: #2e7d32; }
        .attribute.seniority { background: #fff3e0; color: #ef6c00; }
        .attribute.program { background: #fce4ec; color: #c2185b; }
        .loading { text-align: center; padding: 40px; color: #6c757d; }
        .error { background: #f8d7da; color: #721c24; padding: 12px; border-radius: 6px; margin-bottom: 16px; }
        .search-meta {
            background: #f8f9fa; padding: 12px; border-radius: 6px;
            margin-bottom: 16px; font-size: 14px; color: #6c757d;
        }
        
        .extracted-attributes {
            background: #e3f2fd; border: 1px solid #90caf9; border-radius: 6px;
            padding: 12px; margin-bottom: 16px; font-size: 13px;
        }
        
        .extracted-attributes h5 {
            margin: 0 0 8px 0; color: #1565c0; font-size: 14px;
        }
        
        .attribute-group {
            margin-bottom: 8px;
        }
        
        .attribute-type {
            font-weight: bold; text-transform: capitalize; color: #1976d2;
            margin-right: 8px;
        }
        
        .attribute-list {
            display: inline-flex; flex-wrap: wrap; gap: 4px;
        }
        
        .extracted-attribute {
            background: #bbdefb; color: #0d47a1; padding: 2px 6px;
            border-radius: 4px; font-size: 11px; font-weight: 500;
        }
        
        .extracted-attribute.matched {
            background: #c8e6c9; color: #2e7d32; border: 1px solid #4caf50;
        }
        
        .extracted-attribute.no-match {
            background: #ffebee; color: #d32f2f; border: 1px solid #f44336;
        }
        .reset-button {
            width: 100%; padding: 8px; background: #6c757d; color: white;
            border: none; border-radius: 6px; font-size: 14px; cursor: pointer; margin-top: 10px;
        }
        
        .advanced-controls {
            margin-top: 20px;
            border-top: 1px solid #dee2e6;
            padding-top: 15px;
        }
        
        .collapsible-header {
            display: flex;
            align-items: center;
            cursor: pointer;
            padding: 8px 0;
            user-select: none;
        }
        
        .collapsible-header:hover {
            background: rgba(102, 126, 234, 0.1);
            border-radius: 4px;
            padding: 8px;
        }
        
        .toggle-icon {
            margin-right: 8px;
            font-weight: bold;
            transition: transform 0.2s;
        }
        
        .toggle-icon.expanded {
            transform: rotate(90deg);
        }
        
        .collapsible-content {
            display: none;
            margin-top: 10px;
        }
        
        .collapsible-content.expanded {
            display: block;
        }
        
        .setting-description {
            font-size: 12px;
            color: #6c757d;
            margin-left: 8px;
            font-style: italic;
        }
    </style>
</head>
<body>
    <div class="container-fluid">
        <div class="header">
            <div class="nav-links">
                <a href="/ui/search" class="nav-link active">🔍 Search</a>
                <a href="/ui/experts" class="nav-link">👥 All Experts</a>
            </div>
            <h1>Expert Search - Weight Testing</h1>
            <p>Customize attribute weights to see how they affect search results</p>
        </div>
        
        <div class="content">
            <div class="controls">
                <h3>Search Controls</h3>
                
                <textarea id="searchInput" class="search-input" rows="6"
                          placeholder="Enter a search query."></textarea>
                
                <div class="weight-controls">
                    <h4>Attribute Weights</h4>
                    <div class="weight-item">
                        <div class="weight-label">agency</div>
                        <input type="range" class="weight-slider" min="0.1" max="5.0" step="0.1" value="1.5" data-type="agency" />
                        <div class="weight-value" id="agency-value">1.5</div>
                    </div>
                    <div class="weight-item">
                        <div class="weight-label">role</div>
                        <input type="range" class="weight-slider" min="0.1" max="5.0" step="0.1" value="2.0" data-type="role" />
                        <div class="weight-value" id="role-value">2.0</div>
                    </div>
                    <div class="weight-item">
                        <div class="weight-label">seniority</div>
                        <input type="range" class="weight-slider" min="0.1" max="5.0" step="0.1" value="1.0" data-type="seniority" />
                        <div class="weight-value" id="seniority-value">1.0</div>
                    </div>
                    <div class="weight-item">
                        <div class="weight-label">skill</div>
                        <input type="range" class="weight-slider" min="0.1" max="5.0" step="0.1" value="1.8" data-type="skill" />
                        <div class="weight-value" id="skill-value">1.8</div>
                    </div>
                    <div class="weight-item">
                        <div class="weight-label">program</div>
                        <input type="range" class="weight-slider" min="0.1" max="5.0" step="0.1" value="1.2" data-type="program" />
                        <div class="weight-value" id="program-value">1.2</div>
                    </div>
                </div>
                
                <div class="advanced-controls">
                    <div class="collapsible-header" onclick="toggleAdvancedSettings()">
                        <span class="toggle-icon" id="advanced-toggle">▶</span>
                        <h4 style="margin: 0;">Advanced Settings</h4>
                    </div>
                    
                    <div class="collapsible-content" id="advanced-content">
                        <div class="weight-item">
                            <div class="weight-label">
                                Similarity Threshold
                                <div class="setting-description">Min cosine similarity to consider a match (higher = stricter)</div>
                            </div>
                            <input type="range" class="weight-slider" min="0.1" max="1.0" step="0.05" value="0.4" id="similarity-threshold" />
                            <div class="weight-value" id="similarity-threshold-value">0.4</div>
                        </div>
                        <div class="weight-item">
                            <div class="weight-label">
                                Max Similar Attributes
                                <div class="setting-description">Max attributes to consider per search</div>
                            </div>
                            <input type="range" class="weight-slider" min="5" max="50" step="1" value="20" id="max-similar-attributes" />
                            <div class="weight-value" id="max-similar-attributes-value">20</div>
                        </div>
                        <div class="weight-item">
                            <div class="weight-label">
                                Max Attributes Per Type
                                <div class="setting-description">Max attributes of each type to use</div>
                            </div>
                            <input type="range" class="weight-slider" min="1" max="10" step="1" value="3" id="max-attributes-per-type" />
                            <div class="weight-value" id="max-attributes-per-type-value">3</div>
                        </div>
                        <div class="weight-item">
                            <div class="weight-label">
                                Scoring Base
                                <div class="setting-description">Exponential base for score calculation</div>
                            </div>
                            <input type="range" class="weight-slider" min="1.0" max="2.0" step="0.05" value="1.1" id="scoring-base" />
                            <div class="weight-value" id="scoring-base-value">1.1</div>
                        </div>
                        <div class="weight-item">
                            <div class="weight-label">
                                Recency Decay Factor
                                <div class="setting-description">How much older experience reduces score</div>
                            </div>
                            <input type="range" class="weight-slider" min="0.0" max="0.5" step="0.01" value="0.1" id="recency-decay-factor" />
                            <div class="weight-value" id="recency-decay-factor-value">0.1</div>
                        </div>
                    </div>
                </div>
                
                <button class="reset-button" onclick="resetAllSettings()">Reset All to Defaults</button>
                
                <button class="search-button" onclick="performSearch()">Search Experts</button>
            </div>
            
            <div class="results">
                <h3>Search Results</h3>
                <div id="results-content">
                    <div class="loading">Enter a search query and click "Search Experts" to see results</div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const defaultWeights = { agency: 1.5, role: 2.0, seniority: 1.0, skill: 1.8, program: 1.2 };
        const defaultSettings = {
            'similarity-threshold': 0.4,
            'max-similar-attributes': 20,
            'max-attributes-per-type': 3,
            'scoring-base': 1.1,
            'recency-decay-factor': 0.1
        };
        
        // Update value displays for all sliders
        document.querySelectorAll('.weight-slider').forEach(slider => {
            slider.addEventListener('input', function() {
                const type = this.getAttribute('data-type');
                if (type) {
                    // Weight slider
                    document.getElementById(type + '-value').textContent = this.value;
                } else {
                    // Advanced setting slider
                    const id = this.getAttribute('id');
                    document.getElementById(id + '-value').textContent = this.value;
                }
            });
        });
        
        // Update value displays for advanced settings
        document.querySelectorAll('#similarity-threshold, #max-similar-attributes, #max-attributes-per-type, #scoring-base, #recency-decay-factor').forEach(slider => {
            slider.addEventListener('input', function() {
                document.getElementById(this.id + '-value').textContent = this.value;
            });
        });
        
        function resetWeights() {
            Object.keys(defaultWeights).forEach(type => {
                const slider = document.querySelector('[data-type="' + type + '"]');
                slider.value = defaultWeights[type];
                document.getElementById(type + '-value').textContent = defaultWeights[type];
            });
        }
        
        function resetAllSettings() {
            // Reset weights
            resetWeights();
            
            // Reset advanced settings
            Object.keys(defaultSettings).forEach(settingId => {
                const slider = document.getElementById(settingId);
                slider.value = defaultSettings[settingId];
                document.getElementById(settingId + '-value').textContent = defaultSettings[settingId];
            });
        }
        
        function toggleAdvancedSettings() {
            const content = document.getElementById('advanced-content');
            const toggle = document.getElementById('advanced-toggle');
            
            if (content.classList.contains('expanded')) {
                content.classList.remove('expanded');
                toggle.classList.remove('expanded');
                toggle.textContent = '▶';
            } else {
                content.classList.add('expanded');
                toggle.classList.add('expanded');
                toggle.textContent = '▼';
            }
        }
        
        function getWeights() {
            const weights = [];
            document.querySelectorAll('[data-type]').forEach(slider => {
                const type = slider.getAttribute('data-type');
                weights.push({ name: type, weight: parseFloat(slider.value) });
            });
            return weights;
        }
        
        function getAdvancedSettings() {
            return {
                similarity_threshold: parseFloat(document.getElementById('similarity-threshold').value),
                max_similar_attributes: parseInt(document.getElementById('max-similar-attributes').value),
                max_attributes_per_type: parseInt(document.getElementById('max-attributes-per-type').value),
                scoring_base: parseFloat(document.getElementById('scoring-base').value),
                recency_decay_factor: parseFloat(document.getElementById('recency-decay-factor').value)
            };
        }
        
        async function performSearch() {
            const searchText = document.getElementById('searchInput').value.trim();
            if (!searchText) {
                alert('Please enter a search query');
                return;
            }
            
            const resultsDiv = document.getElementById('results-content');
            resultsDiv.innerHTML = '<div class="loading">Searching for experts...</div>';
            
            try {
                const searchSettings = {
                    attribute_weights: getWeights(),
                    ...getAdvancedSettings()
                };
                
                const response = await fetch('/api/experts/search', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        text: searchText,
                        page_size: 10,
                        settings: searchSettings
                    })
                });
                
                if (!response.ok) {
                    throw new Error(`Search failed: ${response.status}`);
                }
                
                const data = await response.json();
                displayResults(data);
                
            } catch (error) {
                resultsDiv.innerHTML = '<div class="error">Error: ' + error.message + '</div>';
            }
        }
        
        function displayResults(data) {
            const resultsDiv = document.getElementById('results-content');
            
            if (!data.experts || data.experts.length === 0) {
                resultsDiv.innerHTML = '<div class="loading">No experts found for your search query.</div>';
                return;
            }
            
            let html = '<div class="search-meta">Found ' + data.search_metadata.total_experts + 
                      ' experts in ' + data.search_metadata.search_time_ms + 'ms</div>';
            
            // Display extracted attributes if available
            if (data.search_metadata.extracted_attributes) {
                html += '<div class="extracted-attributes">';
                html += '  <h5>🔍 Search Analysis - Attributes Found:</h5>';
                html += '  <div style="font-size: 11px; margin-bottom: 8px; color: #666;">';
                html += '    <span class="extracted-attribute matched">✓ Matched</span> ';
                html += '    <span class="extracted-attribute no-match">✗ No Match</span>';
                html += '  </div>';
                
                const extractedAttrs = data.search_metadata.extracted_attributes;
                let hasAttributes = false;
                
                Object.keys(extractedAttrs).forEach(attrType => {
                    if (extractedAttrs[attrType] && extractedAttrs[attrType].length > 0) {
                        hasAttributes = true;
                        html += '  <div class="attribute-group">';
                        html += '    <span class="attribute-type">' + attrType + ':</span>';
                        html += '    <div class="attribute-list">';
                        
                        extractedAttrs[attrType].forEach(attr => {
                            const sourceClass = attr.source ? attr.source.replace('_', '-') : '';
                            html += '      <span class="extracted-attribute ' + sourceClass + '">';
                            html += attr.name + ' (' + (attr.relevance_score ? attr.relevance_score.toFixed(2) : 'N/A') + ')';
                            html += '</span>';
                        });
                        
                        html += '    </div>';
                        html += '  </div>';
                    }
                });
                
                if (!hasAttributes) {
                    html += '  <div style="color: #666; font-style: italic;">No specific attributes extracted - using semantic similarity search</div>';
                }
                
                html += '</div>';
            }
                      
            data.experts.forEach(expert => {
                html += '<div class="expert-card">';
                html += '  <div class="expert-header">';
                html += '    <div class="expert-name">' + expert.name;
                if (expert.meta && expert.meta.profile_id) {
                    html += '<span class="profile-id">ID: ' + expert.meta.profile_id + '</span>';
                }
                html += '</div>';
                html += '    <div class="expert-score">' + expert.total_score + '</div>';
                html += '  </div>';
                html += '  <div class="expert-summary">' + expert.summary + '</div>';
                
                if (expert.matching_experiences && expert.matching_experiences.length > 0) {
                    html += '  <div class="experiences">';
                    expert.matching_experiences.forEach(exp => {
                        html += '    <div class="experience">';
                        html += '      <div class="experience-summary">' + exp.summary + '</div>';
                        html += '      <div class="experience-dates">' + exp.start_date + ' to ' + exp.end_date + ' (Score: ' + exp.score + ')</div>';
                        if (exp.matching_attributes) {
                            html += '      <div class="attributes">';
                            exp.matching_attributes.forEach(attr => {
                                html += '        <span class="attribute ' + attr.type + '">' + attr.name + '</span>';
                            });
                            html += '      </div>';
                        }
                        html += '    </div>';
                    });
                    html += '  </div>';
                }
                html += '</div>';
            });
            
            resultsDiv.innerHTML = html;
        }
        
        // Allow Ctrl+Enter or Cmd+Enter to trigger search in textarea
        document.getElementById('searchInput').addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                e.preventDefault();
                performSearch();
            }
        });
    </script>
</body>
</html>'''

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
