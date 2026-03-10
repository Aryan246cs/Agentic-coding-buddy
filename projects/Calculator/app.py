from flask import Flask, render_template, jsonify

# Initialize the Flask application
app = Flask(__name__)


@app.route('/')
def home():
    """Render the home page with a greeting."""
    return render_template('index.html', greeting='Hello, World!')


@app.route('/health')
def health_check():
    """Simple health check endpoint returning JSON status."""
    # Using jsonify ensures the correct mimetype and formatting
    return jsonify({'status': 'OK'}), 200


if __name__ == '__main__':
    # Run the development server on all interfaces, port 5000
    app.run(host='0.0.0.0', port=5000)
