import sys

sys.modules["colorama"] = None

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os
from dotenv import load_dotenv
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import json
import re
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///geo_tool.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Database Models ---
class Analysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(500), nullable=False)
    title = db.Column(db.String(200))
    geo_score = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    gap_analysis = db.Column(db.Text) # Stored as HTML string
    
    # Relationships
    simulations = db.relationship('Simulation', backref='analysis', lazy=True)
    recommendations = db.relationship('Recommendation', backref='analysis', lazy=True)

class Simulation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    analysis_id = db.Column(db.Integer, db.ForeignKey('analysis.id'), nullable=False)
    engine = db.Column(db.String(50))
    query_used = db.Column(db.String(200))
    simulation_text = db.Column(db.Text)
    visibility_score = db.Column(db.Integer) # 0-100 confidence/visibility

class Recommendation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    analysis_id = db.Column(db.Integer, db.ForeignKey('analysis.id'), nullable=False)
    text = db.Column(db.String(500))

# Create tables
with app.app_context():
    db.create_all()

# Configure Gemini
GENAI_API_KEY = os.getenv("GEMINI_API_KEY")
if GENAI_API_KEY:
    genai.configure(api_key=GENAI_API_KEY)

def crawl_website(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Metadata extraction
        title = soup.title.string if soup.title else "No title found"
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        description = meta_desc['content'] if meta_desc else "No description found"
        
        # Structure analysis
        h1_tags = [h.get_text(strip=True) for h in soup.find_all('h1')]
        h2_tags = [h.get_text(strip=True) for h in soup.find_all('h2')]
        
        # Content extraction (simplified)
        paragraphs = [p.get_text(strip=True) for p in soup.find_all('p')]
        text_content = " ".join(paragraphs)[:5000] 
        
        # Accessibility basic check
        images = soup.find_all('img')
        images_without_alt = [img['src'] for img in images if not img.get('alt')]
        accessibility_score = max(0, 100 - (len(images_without_alt) * 5)) 
        
        return {
            "url": url,
            "title": title,
            "description": description,
            "h1": h1_tags,
            "h2": h2_tags[:5],
            "content_snippet": text_content,
            "accessibility_score": accessibility_score
        }
    except Exception as e:
        return {"error": str(e)}

def analyze_with_gemini(data):
    if not GENAI_API_KEY:
        # Mock response for demonstration
        return {
            "geo_score": 78,
            "gap_analysis": "<ul><li><strong>Missing structured data:</strong> The site lacks Schema.org markup for 'MedicalCondition' and 'Drug'.</li><li><strong>Content depth:</strong> While informative, the content is too concise for deep AI queries.</li><li><strong>Keyword gaps:</strong> Terms like 'migraine treatment options' and 'Pfizer digital health' are underrepresented.</li></ul>",
            "search_engine_simulation": [
                {"engine": "Google AI Overviews", "query": f"What is {data['title']}?", "simulation": "PfizerForAll is a digital platform by Pfizer designed to simplify access to healthcare...", "score": 85},
                {"engine": "Perplexity AI", "query": f"Reviews for {data['url']}", "simulation": "According to Pfizer's official site, PfizerForAll offers direct access to migraine support...", "score": 72},
                {"engine": "ChatGPT Search", "query": f"Tell me about {data['title']}", "simulation": "I found that PfizerForAll provides resources for patients, including appointment scheduling...", "score": 90}
            ],
            "recommendations": [
                "Implement Schema.org structured data for all medical pages.",
                "Create a comprehensive FAQ section to answer common natural language queries.",
                "Optimize for 'conversational' keywords rather than just short-tail terms."
            ]
        }
        
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = f"""
    You are a Generative Engine Optimization (GEO) expert. Analyze the following website data:
    URL: {data['url']}
    Title: {data['title']}
    Description: {data['description']}
    H1 Tags: {data['h1']}
    H2 Tags: {data['h2']}
    Content Snippet: {data['content_snippet']}
    Accessibility Score (Basic): {data['accessibility_score']}
    
    Perform a comprehensive GEO analysis.
    1. **Gap Analysis**: Identify missing keywords, structural weaknesses, and content gaps for Generative AI visibility.
    2. **Search Engine Simulation**: Simulate how this site might appear in Google AI Overviews, Perplexity, and ChatGPT. Generate a specific query for each that a user might ask.
    3. **Scoring**: Give a GEO Score out of 100.
    4. **Recommendations**: Provide 3-5 specific, actionable steps.
    
    Return the response as valid JSON with the following keys:
    "geo_score": integer,
    "gap_analysis": "html string using <ul> and <li> tags",
    "search_engine_simulation": [
        {{"engine": "Google AI Overviews", "query": "specific user query", "simulation": "text", "score": integer (0-100 visibility)}},
        {{"engine": "Perplexity AI", "query": "specific user query", "simulation": "text", "score": integer}},
        {{"engine": "ChatGPT Search", "query": "specific user query", "simulation": "text", "score": integer}}
    ],
    "recommendations": ["rec1", "rec2", "rec3"]
    """
    
    try:
        response = model.generate_content(prompt)
        text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(text)
    except Exception as e:
        return {
            "geo_score": 0,
            "gap_analysis": f"Error generating analysis: {str(e)}",
            "recommendations": [],
            "search_engine_simulation": []
        }

@app.route('/')
def dashboard():
    # Analytics
    total_scans = Analysis.query.count()
    avg_score = db.session.query(db.func.avg(Analysis.geo_score)).scalar() or 0
    recent_analyses = Analysis.query.order_by(Analysis.created_at.desc()).limit(5).all()
    
    return render_template('dashboard.html', 
                         total_scans=total_scans, 
                         avg_score=int(avg_score), 
                         recent_analyses=recent_analyses)

@app.route('/analyze', methods=['POST'])
def analyze():
    url = request.form.get('url')
    if not url:
        return redirect(url_for('dashboard'))
    
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
        
    crawl_data = crawl_website(url)
    
    if "error" in crawl_data:
        # In a real app, flash message here
        return redirect(url_for('dashboard'))
        
    analysis_result = analyze_with_gemini(crawl_data)
    
    # Save to DB
    new_analysis = Analysis(
        url=url,
        title=crawl_data.get('title', url),
        geo_score=analysis_result.get('geo_score', 0),
        gap_analysis=analysis_result.get('gap_analysis', '')
    )
    db.session.add(new_analysis)
    db.session.flush() # Get ID
    
    for sim in analysis_result.get('search_engine_simulation', []):
        db.session.add(Simulation(
            analysis_id=new_analysis.id,
            engine=sim.get('engine'),
            query_used=sim.get('query', 'N/A'),
            simulation_text=sim.get('simulation'),
            visibility_score=sim.get('score', 0)
        ))
        
    for rec in analysis_result.get('recommendations', []):
        db.session.add(Recommendation(
            analysis_id=new_analysis.id,
            text=rec
        ))
        
    db.session.commit()
    
    return redirect(url_for('report', analysis_id=new_analysis.id))

@app.route('/report/<int:analysis_id>')
def report(analysis_id):
    analysis = Analysis.query.get_or_404(analysis_id)
    return render_template('report.html', analysis=analysis)

@app.route('/history')
def history():
    analyses = Analysis.query.order_by(Analysis.created_at.desc()).all()
    return render_template('history.html', analyses=analyses)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
