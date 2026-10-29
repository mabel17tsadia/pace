from flask import Flask, render_template

# Create the Flask app
app = Flask(__name__)


# Show the home page
@app.route("/")
def home():
    return render_template("index.html")


# Start the app in debug mode when this file is run directly
if __name__ == "__main__":
    app.run(debug=True)
