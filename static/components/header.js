/**
 * Shared header component for all Cerca UI views
 */

class CercaHeader {
    constructor(title, subtitle, activeView = null) {
        this.title = title;
        this.subtitle = subtitle;
        this.activeView = activeView;
    }

    render() {
        return `
            <div class="header">
                <nav class="navbar">
                    <div class="nav-links">
                        <a href="/ui/search" class="nav-link ${this.activeView === 'searchv' ? 'active' : ''}">OnFrontiers CERCA</a>
                        <a href="/ui/search" class="nav-link ${this.activeView === 'search' ? 'active' : ''}">🔍 Search</a>
                        <a href="/ui/experts" class="nav-link ${this.activeView === 'experts' ? 'active' : ''}">👥 Experts</a>
                        <a href="/ui/solicitation-roles" class="nav-link ${this.activeView === 'solicitation-roles' ? 'active' : ''}">📋 Solicitation Roles</a>
                        <a href="/ui/prompts" class="nav-link ${this.activeView === 'prompts' ? 'active' : ''}">⚙️ Prompts</a>
                        <a href="/ui/evaluations" class="nav-link ${this.activeView === 'evaluations' ? 'active' : ''}">📊 Evaluations</a>
                    </div>
                </nav>
                <div class="page-header">
                    <h1>${this.title}</h1>
                    <p>${this.subtitle}</p>
                </div>
            </div>
        `;
    }

    // Get the shared CSS styles for the header
    static getStyles() {
        return `
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            
            .navbar {
                display: flex; justify-content: space-between; align-items: center;
                padding: 12px 20px; border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            }
            
            .company-logo {
                font-size: 18px; font-weight: 700; color: white;
                opacity: 0.95;
            }
            
            .nav-links {
                display: flex; gap: 15px; align-items: center;
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
            
            .page-header {
                text-align: center; padding: 30px 20px;
            }
            
            .page-header h1 {
                margin: 0 0 8px 0; font-size: 28px; font-weight: 600;
            }
            
            .page-header p {
                margin: 0; opacity: 0.9; font-size: 16px;
            }
        `;
    }
}

// Make it available globally
window.CercaHeader = CercaHeader;