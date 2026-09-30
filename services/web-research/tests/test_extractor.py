from web_research.extractor import extract_clean_markdown


def test_extract_clean_markdown_strips_scripts_and_styles():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Machine Learning Basics</title>
        <style>body { color: red; }</style>
        <script>alert('malicious payload');</script>
    </head>
    <body>
        <nav><a href="/home">Home</a></nav>
        <header>Header Banner</header>
        <h1>Introduction to Neural Networks</h1>
        <p>Neural networks are computing systems inspired by biological brains.</p>
        <h2>Key Concepts</h2>
        <ul>
            <li>Weights and biases</li>
            <li>Backpropagation</li>
            <li>Activation functions</li>
        </ul>
        <footer>Copyright 2026</footer>
        <script src="tracker.js"></script>
    </body>
    </html>
    """

    result = extract_clean_markdown(html)

    assert result["title"] == "Machine Learning Basics"
    markdown = result["content_markdown"]

    # Verify content was extracted
    assert "# Introduction to Neural Networks" in markdown
    assert "Neural networks are computing systems" in markdown
    assert "## Key Concepts" in markdown
    assert "- Weights and biases" in markdown
    assert "- Backpropagation" in markdown

    # Verify script, style, header, footer were stripped
    assert "malicious payload" not in markdown
    assert "color: red" not in markdown
    assert "Header Banner" not in markdown
    assert "Copyright 2026" not in markdown
    assert len(result["snippet"]) > 0
