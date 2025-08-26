import re
from flask import Flask, request, render_template, jsonify, send_from_directory
import os
import zipfile
import tempfile
import shutil
from pathlib import Path
import json
import time
from datetime import datetime
import openai
from werkzeug.utils import secure_filename
import threading
import queue

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['REPORTS_FOLDER'] = 'reports'

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['REPORTS_FOLDER'], exist_ok=True)
os.makedirs('templates', exist_ok=True)
os.makedirs('static', exist_ok=True)

# OpenAI Configuration
openai.api_key = os.getenv('OPENAI_API_KEY')

class DotNetMigrationAnalyzer:
    def __init__(self, project_path, report_id):
        self.project_path = project_path
        self.report_id = report_id
        self.analysis_data = {
            'files_and_folders': {},
            'readme_and_comments': [],
            'executive_summary': '',
            'migration_steps': {},
            'project_structure': {},
            'dependencies': [],
            'configuration_files': {},
            'code_analysis': {}
        }
        self.progress = 0
        self.status = "Starting analysis..."

    def analyze_project(self):
        """Main analysis pipeline"""
        try:
            self.status = "Step 1: Crawling project structure..."
            self.progress = 10
            self.crawl_project()
            
            self.status = "Step 2: Listing files and folders..."
            self.progress = 20
            self.list_files_and_folders()
            
            self.status = "Step 3: Extracting README and comments..."
            self.progress = 30
            self.extract_readme_and_comments()
            
            self.status = "Step 4: Analyzing codebase with AI..."
            self.progress = 40
            self.analyze_codebase_with_ai()
            
            self.status = "Step 5: Generating executive summary..."
            self.progress = 60
            self.generate_executive_summary()
            
            self.status = "Step 6: Creating detailed migration steps..."
            self.progress = 80
            self.generate_migration_steps()
            
            self.status = "Step 7: Generating final report..."
            self.progress = 90
            self.generate_final_report()
            
            self.status = "Analysis completed!"
            self.progress = 100
            return True
            
        except Exception as e:
            self.status = f"Error: {str(e)}"
            return False

    def crawl_project(self):
        """Crawl the project directory and catalog all files"""
        self.analysis_data['project_structure'] = self._build_directory_tree(self.project_path)

    def _build_directory_tree(self, path, max_depth=5, current_depth=0):
        """Build a nested dictionary representing the directory structure"""
        if current_depth > max_depth:
            return {}
        
        tree = {}
        try:
            for item in Path(path).iterdir():
                if item.name.startswith('.'):
                    continue
                    
                if item.is_file():
                    tree[item.name] = {
                        'type': 'file',
                        'size': item.stat().st_size,
                        'extension': item.suffix.lower()
                    }
                elif item.is_dir():
                    tree[item.name] = {
                        'type': 'directory',
                        'children': self._build_directory_tree(item, max_depth, current_depth + 1)
                    }
        except PermissionError:
            pass
        return tree

    def list_files_and_folders(self):
        """Create comprehensive lists of files and folders with categorization"""
        files_by_type = {
            'source_code': [],
            'project_files': [],
            'configuration': [],
            'documentation': [],
            'resources': [],
            'other': []
        }
        
        folders = []
        
        for root, dirs, files in os.walk(self.project_path):
            # Skip hidden and common ignored directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d.lower() not in ['bin', 'obj', 'packages', 'node_modules']]
            
            rel_root = os.path.relpath(root, self.project_path)
            if rel_root != '.':
                folders.append(rel_root)
            
            for file in files:
                if file.startswith('.'):
                    continue
                    
                file_path = os.path.join(rel_root, file) if rel_root != '.' else file
                file_ext = Path(file).suffix.lower()
                
                file_info = {
                    'name': file,
                    'path': file_path,
                    'size': os.path.getsize(os.path.join(root, file)),
                    'extension': file_ext
                }
                
                # Categorize files
                if file_ext in ['.cs', '.vb', '.aspx', '.ascx', '.ashx']:
                    files_by_type['source_code'].append(file_info)
                elif file_ext in ['.csproj', '.vbproj', '.sln', '.proj']:
                    files_by_type['project_files'].append(file_info)
                elif file.lower() in ['web.config', 'app.config', 'appsettings.json', 'packages.config']:
                    files_by_type['configuration'].append(file_info)
                elif file_ext in ['.md', '.txt', '.doc', '.docx'] or 'readme' in file.lower():
                    files_by_type['documentation'].append(file_info)
                elif file_ext in ['.css', '.js', '.html', '.htm', '.jpg', '.png', '.gif']:
                    files_by_type['resources'].append(file_info)
                else:
                    files_by_type['other'].append(file_info)
        
        self.analysis_data['files_and_folders'] = {
            'files_by_type': files_by_type,
            'folders': folders,
            'total_files': sum(len(files) for files in files_by_type.values()),
            'total_folders': len(folders)
        }

    def extract_readme_and_comments(self):
        """Extract README files and code comments"""
        readme_content = []
        comments_summary = []
        
        # Find and read README files
        for root, dirs, files in os.walk(self.project_path):
            for file in files:
                if 'readme' in file.lower() or file.lower().endswith('.md'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()[:2000]  # Limit content
                            readme_content.append({
                                'file': file,
                                'path': os.path.relpath(file_path, self.project_path),
                                'content': content
                            })
                    except:
                        pass
        
        # Extract comments from source files
        source_files = self.analysis_data['files_and_folders']['files_by_type']['source_code'][:20]  # Limit to first 20 files
        for file_info in source_files:
            file_path = os.path.join(self.project_path, file_info['path'])
            comments = self._extract_comments_from_file(file_path)
            if comments:
                comments_summary.append({
                    'file': file_info['name'],
                    'comments': comments[:10]  # Limit comments per file
                })
        
        self.analysis_data['readme_and_comments'] = {
            'readme_files': readme_content,
            'code_comments': comments_summary
        }

    def _extract_comments_from_file(self, file_path):
        """Extract comments from a source code file"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Extract single-line and multi-line comments
            comments = []
            
            # Single-line comments (//)
            single_line_pattern = r'//\s*(.+)'
            single_comments = re.findall(single_line_pattern, content)
            comments.extend([c.strip() for c in single_comments if c.strip()])
            
            # Multi-line comments (/* */)
            multi_line_pattern = r'/\*(.*?)\*/'
            multi_comments = re.findall(multi_line_pattern, content, re.DOTALL)
            comments.extend([c.strip() for c in multi_comments if c.strip()])
            
            # XML documentation comments (///)
            xml_doc_pattern = r'///\s*(.+)'
            xml_comments = re.findall(xml_doc_pattern, content)
            comments.extend([c.strip() for c in xml_comments if c.strip()])
            
            return comments[:20]  # Limit to 20 comments per file
        except:
            return []

    def analyze_codebase_with_ai(self):
        """Use OpenAI to analyze the codebase structure and dependencies"""
        # Prepare analysis prompt
        structure_summary = self._prepare_structure_summary()
        
        prompt = f"""
        Analyze this .NET codebase structure and provide insights:

        PROJECT STRUCTURE:
        {json.dumps(structure_summary, indent=2)}

        Please analyze and provide:
        1. Project type identification (Web Forms, MVC, Web API, Console, etc.)
        2. .NET Framework version detection
        3. Key dependencies and technologies used
        4. Architecture patterns identified
        5. Potential migration challenges
        6. Security concerns
        7. Performance considerations

        Respond in JSON format with these sections.
        """
        
        try:
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a senior .NET architect specializing in legacy code migration to cloud platforms."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.3
            )
            
            ai_analysis = response.choices[0].message.content
            # Try to parse as JSON, fall back to text if needed
            try:
                self.analysis_data['code_analysis'] = json.loads(ai_analysis)
            except:
                self.analysis_data['code_analysis'] = {'raw_analysis': ai_analysis}
                
        except Exception as e:
            self.analysis_data['code_analysis'] = {'error': str(e)}

    def _prepare_structure_summary(self):
        """Prepare a concise summary of project structure for AI analysis"""
        summary = {
            'total_files': self.analysis_data['files_and_folders']['total_files'],
            'total_folders': self.analysis_data['files_and_folders']['total_folders'],
            'file_types': {},
            'key_files': [],
            'configuration_files': []
        }
        
        # Summarize file types
        for file_type, files in self.analysis_data['files_and_folders']['files_by_type'].items():
            summary['file_types'][file_type] = len(files)
            if file_type in ['project_files', 'configuration']:
                summary['key_files'].extend([f['name'] for f in files[:10]])
        
        # Add sample of source files
        source_files = self.analysis_data['files_and_folders']['files_by_type']['source_code'][:20]
        summary['source_files_sample'] = [f['name'] for f in source_files]
        
        return summary

    def generate_executive_summary(self):
        """Generate executive summary using AI"""
        analysis_data = self.analysis_data
        
        prompt = f"""
        Create an executive summary for this .NET legacy codebase migration analysis:

        PROJECT OVERVIEW:
        - Total files: {analysis_data['files_and_folders']['total_files']}
        - Source code files: {len(analysis_data['files_and_folders']['files_by_type']['source_code'])}
        - Project files: {len(analysis_data['files_and_folders']['files_by_type']['project_files'])}

        AI ANALYSIS:
        {json.dumps(analysis_data.get('code_analysis', {}), indent=2)}

        README CONTENT:
        {json.dumps(analysis_data['readme_and_comments']['readme_files'][:2], indent=2)}

        Create a 3-paragraph executive summary covering:
        1. Current state of the application
        2. Key technical challenges for migration
        3. Recommended migration approach and timeline estimate
        """
        
        try:
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a senior technical consultant specializing in .NET modernization projects."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.4
            )
            
            self.analysis_data['executive_summary'] = response.choices[0].message.content
        except Exception as e:
            self.analysis_data['executive_summary'] = f"Error generating summary: {str(e)}"

    def generate_migration_steps(self):
        """Generate detailed migration steps using AI"""
        categories = [
            "environment_setup",
            "code_analysis_and_inventory", 
            "dependency_migration",
            "configuration_migration",
            "database_migration",
            "testing_strategy",
            "deployment_preparation",
            "post_migration_tasks"
        ]
        
        migration_steps = {}
        
        for category in categories:
            self.progress += 2  # Increment progress for each category
            migration_steps[category] = self._generate_category_steps(category)
            time.sleep(0.5)  # Brief pause between API calls
        
        self.analysis_data['migration_steps'] = migration_steps

    def _generate_category_steps(self, category):
        """Generate detailed steps for a specific migration category"""
        category_prompts = {
            "environment_setup": f"""
            Based on this .NET project analysis, provide detailed environment setup steps:
            
            Project Type: {self.analysis_data.get('code_analysis', {}).get('project_type', 'Unknown')}
            Current Framework: {self.analysis_data.get('code_analysis', {}).get('framework_version', '.NET Framework')}
            
            Provide step-by-step instructions for:
            1. Installing required SDKs and tools
            2. Setting up development environment
            3. Configuring cloud platform tools
            4. Installing migration utilities
            
            Include exact commands, download links, and version requirements.
            """,
            
            "code_analysis_and_inventory": """
            Provide detailed steps for analyzing the legacy codebase:
            1. Using .NET Portability Analyzer - exact steps with screenshots
            2. Running try-convert tool - command line examples
            3. Dependency analysis tools - which tools to use and how
            4. Creating migration inventory spreadsheet
            
            Include specific commands, tool configurations, and expected outputs.
            """,
            
            "dependency_migration": f"""
            Based on the analyzed dependencies, provide detailed migration steps:
            
            Dependencies found: {self.analysis_data.get('code_analysis', {}).get('dependencies', [])}
            
            For each dependency provide:
            1. Exact NuGet commands to remove old packages
            2. Exact commands to install new packages
            3. Code changes required
            4. Testing steps to verify migration
            
            Include version compatibility matrices and breaking changes.
            """,
            
            "configuration_migration": """
            Provide step-by-step configuration migration:
            1. Converting web.config/app.config to appsettings.json
            2. Migrating connection strings
            3. Setting up dependency injection
            4. Environment-specific configurations
            
            Include before/after code examples and exact transformation steps.
            """,
            
            "database_migration": """
            Provide database migration strategy:
            1. Assessing current database compatibility
            2. Planning migration approach (lift-and-shift vs modernization)
            3. Data migration tools and steps
            4. Connection string updates
            5. Cloud database configuration
            
            Include specific Azure SQL/AWS RDS setup steps.
            """,
            
            "testing_strategy": """
            Provide comprehensive testing approach:
            1. Setting up automated testing framework
            2. Creating migration test cases
            3. Performance testing strategy
            4. Security testing requirements
            5. User acceptance testing plan
            
            Include test framework setup commands and sample test cases.
            """,
            
            "deployment_preparation": """
            Provide cloud deployment preparation steps:
            1. Containerization with Docker
            2. CI/CD pipeline setup
            3. Infrastructure as Code templates
            4. Monitoring and logging configuration
            5. Security configuration
            
            Include exact Azure DevOps/GitHub Actions configurations.
            """,
            
            "post_migration_tasks": """
            Provide post-migration checklist:
            1. Performance optimization steps
            2. Security hardening
            3. Monitoring setup validation
            4. Documentation updates
            5. Team training requirements
            
            Include verification scripts and monitoring dashboards setup.
            """
        }
        
        prompt = category_prompts.get(category, f"Provide detailed steps for {category} migration.")
        
        try:
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a senior .NET migration specialist. Provide detailed, actionable steps with exact commands and configurations."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.2
            )
            
            return {
                'category': category.replace('_', ' ').title(),
                'content': response.choices[0].message.content,
                'generated_at': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'category': category.replace('_', ' ').title(),
                'content': f"Error generating steps: {str(e)}",
                'generated_at': datetime.now().isoformat()
            }

    def generate_final_report(self):
        """Generate and save the final comprehensive report"""
        report = {
            'metadata': {
                'report_id': self.report_id,
                'generated_at': datetime.now().isoformat(),
                'project_path': self.project_path,
                'analysis_version': '1.0'
            },
            'analysis_data': self.analysis_data
        }
        
        # Save detailed JSON report
        report_path = os.path.join(app.config['REPORTS_FOLDER'], f'{self.report_id}.json')
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        # Generate HTML report
        self._generate_html_report(report)

    def _generate_html_report(self, report):
        """Generate HTML report from analysis data"""
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>.NET Migration Analysis Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
                .header { background: #2196F3; color: white; padding: 20px; margin: -40px -40px 40px -40px; }
                .section { margin: 30px 0; padding: 20px; border-left: 4px solid #2196F3; background: #f9f9f9; }
                .step-item { background: white; margin: 10px 0; padding: 15px; border-radius: 5px; }
                pre { background: #f4f4f4; padding: 15px; overflow-x: auto; }
                .progress { background: #e0e0e0; height: 20px; border-radius: 10px; }
                .progress-bar { background: #4CAF50; height: 100%; border-radius: 10px; width: 100%; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>.NET Legacy Migration Analysis Report</h1>
                <p>Generated: {{ generated_at }}</p>
                <div class="progress"><div class="progress-bar"></div></div>
                <p>Analysis Complete</p>
            </div>
            
            <div class="section">
                <h2>Executive Summary</h2>
                <p>{{ executive_summary }}</p>
            </div>
            
            <div class="section">
                <h2>Project Structure Analysis</h2>
                <p><strong>Total Files:</strong> {{ total_files }}</p>
                <p><strong>Total Folders:</strong> {{ total_folders }}</p>
                <h3>Files by Type:</h3>
                <ul>
                {% for file_type, count in files_by_type.items() %}
                    <li>{{ file_type|title }}: {{ count }} files</li>
                {% endfor %}
                </ul>
            </div>
            
            {% for category, steps in migration_steps.items() %}
            <div class="section">
                <h2>{{ steps.category }}</h2>
                <div class="step-item">
                    <pre>{{ steps.content }}</pre>
                </div>
            </div>
            {% endfor %}
        </body>
        </html>
        """
        
        # This would need Jinja2 template rendering in a full implementation
        # For now, save as a simple HTML file
        html_path = os.path.join(app.config['REPORTS_FOLDER'], f'{self.report_id}.html')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(f"<h1>Migration Report {self.report_id}</h1><pre>{json.dumps(report, indent=2)}</pre>")

# Global dictionary to track analysis progress
analysis_progress = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_project():
    if 'project_file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['project_file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Generate unique report ID
    report_id = f"report_{int(time.time())}_{file.filename.split('.')[0]}"
    
    # Save uploaded file
    filename = secure_filename(file.filename)
    upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(upload_path)
    
    # Extract if it's a zip file
    extraction_path = os.path.join(app.config['UPLOAD_FOLDER'], report_id)
    if filename.lower().endswith('.zip'):
        with zipfile.ZipFile(upload_path, 'r') as zip_ref:
            zip_ref.extractall(extraction_path)
        os.remove(upload_path)  # Clean up zip file
    else:
        # If single file, create directory and move file
        os.makedirs(extraction_path, exist_ok=True)
        shutil.move(upload_path, os.path.join(extraction_path, filename))
    
    # Initialize progress tracking
    analysis_progress[report_id] = {
        'status': 'Uploaded',
        'progress': 0,
        'analyzer': None
    }
    
    # Start analysis in background thread
    analyzer = DotNetMigrationAnalyzer(extraction_path, report_id)
    analysis_progress[report_id]['analyzer'] = analyzer
    
    def run_analysis():
        analyzer.analyze_project()
    
    analysis_thread = threading.Thread(target=run_analysis)
    analysis_thread.daemon = True
    analysis_thread.start()
    
    return jsonify({'report_id': report_id, 'status': 'Analysis started'})

@app.route('/progress/<report_id>')
def get_progress(report_id):
    if report_id not in analysis_progress:
        return jsonify({'error': 'Report not found'}), 404
    
    analyzer = analysis_progress[report_id]['analyzer']
    return jsonify({
        'progress': analyzer.progress,
        'status': analyzer.status,
        'completed': analyzer.progress >= 100
    })

@app.route('/report/<report_id>')
def get_report(report_id):
    report_path = os.path.join(app.config['REPORTS_FOLDER'], f'{report_id}.json')
    if not os.path.exists(report_path):
        return jsonify({'error': 'Report not ready'}), 404
    
    with open(report_path, 'r', encoding='utf-8') as f:
        report = json.load(f)
    
    return jsonify(report)

@app.route('/report/<report_id>/html')
def get_html_report(report_id):
    html_path = os.path.join(app.config['REPORTS_FOLDER'], f'{report_id}.html')
    if not os.path.exists(html_path):
        return "Report not ready", 404
    
    return send_from_directory(app.config['REPORTS_FOLDER'], f'{report_id}.html')

if __name__ == '__main__':
    # Create templates/index.html
    index_html = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Real .NET Migration Analyzer</title>
    <style>
        body {
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: rgba(255,255,255,0.95);
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        }
        h1 { color: #2196F3; text-align: center; margin-bottom: 30px; }
        .upload-area {
            border: 2px dashed #2196F3;
            padding: 40px;
            text-align: center;
            border-radius: 15px;
            background: #f8f9ff;
            margin: 30px 0;
            transition: all 0.3s ease;
        }
        .upload-area:hover {
            border-color: #1976D2;
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(33, 150, 243, 0.1);
        }
        .btn {
            background: linear-gradient(135deg, #2196F3, #1976D2);
            color: white;
            padding: 15px 30px;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            font-size: 16px;
            margin: 10px;
            transition: all 0.3s ease;
        }
        .btn:hover { 
            transform: translateY(-2px); 
            box-shadow: 0 8px 15px rgba(33, 150, 243, 0.3);
        }
        .btn:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }
        .progress-section {
            display: none;
            margin: 30px 0;
            text-align: center;
        }
        .progress-bar {
            background: #e0e0e0;
            height: 25px;
            border-radius: 15px;
            overflow: hidden;
            margin: 20px 0;
        }
        .progress-fill {
            background: linear-gradient(90deg, #2196F3, #21CBF3);
            height: 100%;
            width: 0%;
            transition: width 0.5s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
        }
        .results-section {
            display: none;
            margin: 30px 0;
        }
        .section-card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            margin: 20px 0;
            box-shadow: 0 5px 15px rgba(0,0,0,0.08);
            border-left: 5px solid #2196F3;
        }
        .section-title {
            color: #2196F3;
            font-size: 1.5em;
            margin-bottom: 15px;
            font-weight: bold;
        }
        pre {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            overflow-x: auto;
            max-height: 400px;
            border: 1px solid #e9ecef;
            line-height: 1.4;
        }
        .file-info {
            background: #e3f2fd;
            padding: 10px 15px;
            border-radius: 8px;
            margin: 10px 0;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }
        .status-text {
            font-size: 1.1em;
            margin: 15px 0;
            padding: 15px;
            background: #e3f2fd;
            border-radius: 10px;
            border-left: 4px solid #2196F3;
        }
        .error {
            background: #ffebee;
            border-left-color: #f44336;
            color: #c62828;
        }
        .success {
            background: #e8f5e8;
            border-left-color: #4caf50;
            color: #2e7d32;
        }
        .report-buttons {
            text-align: center;
            margin: 20px 0;
        }
        .btn-secondary {
            background: linear-gradient(135deg, #4CAF50, #45a049);
        }
        .btn-secondary:hover {
            box-shadow: 0 8px 15px rgba(76, 175, 80, 0.3);
        }
        .analysis-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        .stat-card {
            background: linear-gradient(135deg, #f8f9fa, #e9ecef);
            padding: 20px;
            border-radius: 12px;
            text-align: center;
            border: 1px solid #dee2e6;
        }
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            color: #2196F3;
        }
        .loading-spinner {
            width: 40px;
            height: 40px;
            border: 4px solid #f3f3f3;
            border-top: 4px solid #2196F3;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 20px auto;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .collapsible {
            cursor: pointer;
            padding: 10px;
            background: #f1f3f4;
            border: none;
            text-align: left;
            width: 100%;
            border-radius: 5px;
            margin: 5px 0;
            font-weight: bold;
        }
        .collapsible:hover {
            background: #e8eaed;
        }
        .collapsible-content {
            display: none;
            padding: 15px;
            background: #fafafa;
            border-radius: 0 0 5px 5px;
        }
        .collapsible.active + .collapsible-content {
            display: block;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 Real .NET Migration Analyzer</h1>
        <p style="text-align: center; font-size: 1.1em;">Upload your .NET project for comprehensive cloud migration analysis using OpenAI GPT-4</p>
        
        <div class="upload-area" id="uploadArea">
            <h3>📁 Upload Your .NET Project</h3>
            <p>Select a ZIP file containing your .NET project or drag and drop it here</p>
            <input type="file" id="fileInput" accept=".zip,.cs,.csproj,.sln,.vb,.config,.json" style="display: none;">
            <button class="btn" onclick="document.getElementById('fileInput').click()">
                Choose File
            </button>
            <div id="fileInfo" class="file-info" style="display: none;"></div>
            <button id="analyzeBtn" class="btn" onclick="startAnalysis()" disabled>
                🚀 Start AI Analysis
            </button>
        </div>

        <div id="progressSection" class="progress-section">
            <div class="loading-spinner"></div>
            <h3>Analyzing Your .NET Project</h3>
            <div id="statusText" class="status-text">Initializing analysis...</div>
            <div class="progress-bar">
                <div id="progressFill" class="progress-fill">0%</div>
            </div>
            <p><em>This process uses OpenAI GPT-4 to analyze your codebase and may take 2-5 minutes depending on project size.</em></p>
        </div>

        <div id="resultsSection" class="results-section">
            <h2>📊 Analysis Results</h2>
            <div class="report-buttons">
                <button id="viewReportBtn" class="btn btn-secondary" onclick="viewReport()">
                    📋 View Detailed Report
                </button>
                <button id="downloadReportBtn" class="btn" onclick="downloadReport()">
                    💾 Download Report
                </button>
            </div>
            <div id="reportContent"></div>
        </div>
    </div>

    <script>
        let currentReportId = null;
        let progressInterval = null;

        document.getElementById('fileInput').addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                const fileInfo = document.getElementById('fileInfo');
                fileInfo.innerHTML = `
                    <strong>Selected:</strong> ${file.name}<br>
                    <strong>Size:</strong> ${(file.size / (1024*1024)).toFixed(2)} MB<br>
                    <strong>Type:</strong> ${file.type || 'Unknown'}
                `;
                fileInfo.style.display = 'block';
                document.getElementById('analyzeBtn').disabled = false;
            }
        });

        // Drag and drop functionality
        const uploadArea = document.getElementById('uploadArea');
        
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.style.borderColor = '#1976D2';
            uploadArea.style.backgroundColor = '#e3f2fd';
        });

        uploadArea.addEventListener('dragleave', (e) => {
            e.preventDefault();
            uploadArea.style.borderColor = '#2196F3';
            uploadArea.style.backgroundColor = '#f8f9ff';
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.style.borderColor = '#2196F3';
            uploadArea.style.backgroundColor = '#f8f9ff';
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                document.getElementById('fileInput').files = files;
                document.getElementById('fileInput').dispatchEvent(new Event('change'));
            }
        });

        async function startAnalysis() {
            const fileInput = document.getElementById('fileInput');
            const file = fileInput.files[0];
            
            if (!file) {
                alert('Please select a file first.');
                return;
            }

            // Show progress section
            document.getElementById('progressSection').style.display = 'block';
            document.getElementById('resultsSection').style.display = 'none';
            document.getElementById('analyzeBtn').disabled = true;

            // Upload file
            const formData = new FormData();
            formData.append('project_file', file);

            try {
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();
                
                if (response.ok) {
                    currentReportId = result.report_id;
                    startProgressTracking();
                } else {
                    showError(result.error || 'Upload failed');
                }
            } catch (error) {
                showError('Network error: ' + error.message);
            }
        }

        function startProgressTracking() {
            progressInterval = setInterval(async () => {
                try {
                    const response = await fetch(`/progress/${currentReportId}`);
                    const progress = await response.json();

                    updateProgress(progress.progress, progress.status);

                    if (progress.completed) {
                        clearInterval(progressInterval);
                        loadResults();
                    }
                } catch (error) {
                    console.error('Progress tracking error:', error);
                }
            }, 2000);
        }

        function updateProgress(percentage, status) {
            const progressFill = document.getElementById('progressFill');
            const statusText = document.getElementById('statusText');
            
            progressFill.style.width = percentage + '%';
            progressFill.textContent = Math.round(percentage) + '%';
            statusText.textContent = status;
            statusText.className = 'status-text';
        }

        async function loadResults() {
            try {
                const response = await fetch(`/report/${currentReportId}`);
                const report = await response.json();

                if (response.ok) {
                    displayResults(report);
                    document.getElementById('resultsSection').style.display = 'block';
                    updateProgress(100, 'Analysis completed successfully!');
                    document.getElementById('progressSection').style.display = 'none';
                } else {
                    showError('Failed to load report: ' + (report.error || 'Unknown error'));
                }
            } catch (error) {
                showError('Failed to load results: ' + error.message);
            }
        }

        function displayResults(report) {
            const data = report.analysis_data;
            const content = document.getElementById('reportContent');
            
            let html = `
                <div class="analysis-grid">
                    <div class="stat-card">
                        <div class="stat-number">${data.files_and_folders?.total_files || 0}</div>
                        <div>Total Files</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">${data.files_and_folders?.total_folders || 0}</div>
                        <div>Folders</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">${data.files_and_folders?.files_by_type?.source_code?.length || 0}</div>
                        <div>Source Files</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">${Object.keys(data.migration_steps || {}).length}</div>
                        <div>Migration Steps</div>
                    </div>
                </div>

                <div class="section-card">
                    <div class="section-title">📝 Executive Summary</div>
                    <p>${data.executive_summary || 'Summary not available'}</p>
                </div>

                <div class="section-card">
                    <div class="section-title">🤖 AI Code Analysis</div>
                    <pre>${JSON.stringify(data.code_analysis || {}, null, 2)}</pre>
                </div>
            `;

            // Add migration steps
            if (data.migration_steps) {
                html += '<div class="section-card"><div class="section-title">🚀 Detailed Migration Steps</div>';
                
                Object.entries(data.migration_steps).forEach(([key, step]) => {
                    html += `
                        <button class="collapsible" onclick="toggleCollapsible(this)">
                            ${step.category} ▼
                        </button>
                        <div class="collapsible-content">
                            <pre>${step.content}</pre>
                            <small><em>Generated: ${new Date(step.generated_at).toLocaleString()}</em></small>
                        </div>
                    `;
                });
                
                html += '</div>';
            }

            // Add file structure
            if (data.files_and_folders) {
                html += `
                    <div class="section-card">
                        <div class="section-title">📁 Project Structure</div>
                        <button class="collapsible" onclick="toggleCollapsible(this)">
                            Files by Type ▼
                        </button>
                        <div class="collapsible-content">
                            <pre>${JSON.stringify(data.files_and_folders.files_by_type, null, 2)}</pre>
                        </div>
                    </div>
                `;
            }

            content.innerHTML = html;
        }

        function toggleCollapsible(element) {
            element.classList.toggle('active');
            const content = element.nextElementSibling;
            content.style.display = content.style.display === 'block' ? 'none' : 'block';
        }

        function showError(message) {
            const statusText = document.getElementById('statusText');
            statusText.textContent = message;
            statusText.className = 'status-text error';
            
            if (progressInterval) {
                clearInterval(progressInterval);
            }
            
            document.getElementById('analyzeBtn').disabled = false;
        }

        function viewReport() {
            if (currentReportId) {
                window.open(`/report/${currentReportId}/html`, '_blank');
            }
        }

        function downloadReport() {
            if (currentReportId) {
                const link = document.createElement('a');
                link.href = `/report/${currentReportId}`;
                link.download = `migration_report_${currentReportId}.json`;
                link.click();
            }
        }

        // Check for OpenAI API key on load
        window.addEventListener('load', () => {
            // You might want to add a check here for API key availability
            console.log('Migration Analyzer loaded. Make sure OPENAI_API_KEY environment variable is set.');
        });
    </script>
</body>
</html>
    '''
    
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(index_html)
    
    print("Starting .NET Migration Analyzer")
    print("Make sure to set OPENAI_API_KEY environment variable")
    print("Open http://localhost:5000 in your browser")
    print("Upload a .NET project ZIP file or individual files")
    print("The AI will analyze your code and provide migration steps")
    
    app.run(debug=True, host='0.0.0.0', port=5000)