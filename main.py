import subprocess
from threading import Thread
from python_app.app import app

def start_ts_app():
    """Ejecuta la aplicación TypeScript."""
    subprocess.run(["pnpm", "run", "dev"], cwd="ts_app")

def start_flask_app():
    """Ejecuta la aplicación Flask."""
    app.run(debug=True, port=5146)

if __name__ == "__main__":
    ts_thread = Thread(target=start_ts_app)
    ts_thread.start()

    start_flask_app()
