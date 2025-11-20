# GEO Tool - Generative Engine Optimization

A modern web tool to analyze websites for Generative Engine Optimization (GEO). It helps you understand how your site might appear in AI search engines like Google AI Overviews, Perplexity, and ChatGPT.

## Features
- **Gap Analysis**: Identifies content and structural gaps.
- **AI Search Simulation**: Simulates how AI engines might cite your site.
- **Scoring System**: Provides a GEO Score (0-100).
- **Recommendations**: Actionable steps to improve visibility.

## Setup

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Configure API Key**:
    - Open `.env` file.
    - Add your Google Gemini API Key: `GEMINI_API_KEY=your_key_here`
    - You can get a key from [Google AI Studio](https://aistudio.google.com/).

3.  **Run the App**:
    ```bash
    python app.py
    ```

4.  **Open in Browser**:
    Go to `http://127.0.0.1:5000`
