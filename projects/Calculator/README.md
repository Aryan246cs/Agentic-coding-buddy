# TestApp

**TestApp** is a simple Flask web application that demonstrates a basic API with health checks and a customizable greeting. It is containerized with Docker for easy deployment, but can also be run directly on a local Python environment.

---

## Prerequisites

- **Docker** (for containerized execution)
- **Python 3.11** (if running locally)

---

## Setup Instructions

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. **Build the Docker image**
   ```bash
   docker build -t testapp .
   ```

3. **Run the container**
   ```bash
   docker run -p 5000:5000 testapp
   ```
   The application will be accessible at `http://localhost:5000`.

4. **Alternatively, run the app locally**
   ```bash
   pip install -r requirements.txt
   python app.py
   ```
   The app will start on port 5000 by default.

---

## Available Endpoints

| Method | Path   | Description                                 |
|--------|--------|---------------------------------------------|
| GET    | `/`    | Displays a greeting message.               |
| GET    | `/health` | Returns a JSON health check: `{ "status": "OK" }` |

---

## Customizing the Greeting

The greeting displayed at the root endpoint (`/`) is defined by the `greeting` variable inside the `home()` view function (found in `app.py`). To change the message, edit that variable and restart the application.

```python
# app.py
@app.route('/')
def home():
    greeting = "Hello, World!"  # <-- modify this string
    return greeting
```

---

## Reference

This README serves as the user guide for TestApp and references all other files in the repository.
