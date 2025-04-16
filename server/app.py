import subprocess
import json
import logging
from flask import Flask, request, jsonify

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def get_container_entrypoint(image: str) -> tuple[list[str], list[str]]:
    """Get the entrypoint and cmd of a Docker image using docker inspect."""
    try:
        logger.info(f"Inspecting image '{image}' for entrypoint and cmd")
        result = subprocess.run(
            ["docker", "inspect", image],
            check=True,
            capture_output=True,
            text=True
        )
        inspect_data = json.loads(result.stdout)
        if not inspect_data:
            logger.warning(f"No inspect data found for image '{image}'")
            return [], []

        config = inspect_data[0].get('Config', {})
        entrypoint = config.get('Entrypoint', []) or []
        cmd = config.get('Cmd', []) or []
        logger.info(f"Found entrypoint: {entrypoint}, cmd: {cmd}")
        return entrypoint, cmd
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to inspect image '{image}': {e.stderr}")
        return [], []
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse docker inspect output for '{image}': {e}")
        return [], []
    except IndexError as e:
        logger.error(f"Unexpected docker inspect output format for '{image}': {e}")
        return [], []

def check_file_for_mlflow(image: str, filepath: str) -> bool:
    """Check if a specific file contains MLflow-related content with strict requirements."""
    try:
        logger.info(f"Checking file '{filepath}' in image '{image}' for MLflow usage")
        result = subprocess.run(
            ["docker", "run", "--rm", image, "cat", filepath],
            check=True,
            capture_output=True,
            text=True
        )
        content = result.stdout.lower()

        # Require mlflow import
        if 'import mlflow' not in content and 'from mlflow' not in content:
            logger.info(f"No MLflow import found in {filepath}")
            return False

        # Require start_run
        if 'mlflow.start_run' not in content:
            logger.info(f"No MLflow start_run found in {filepath}")
            return False

        # Require at least one logging operation
        logging_operations = [
            'mlflow.log_param',
            'mlflow.log_metric',
            'mlflow.log_artifact',
            'mlflow.log_figure',
            'mlflow.log_model',
            'mlflow.log_table',
            'mlflow.log_dict',
            'mlflow.log_image',
            'mlflow.log_text',
        ]

        if not any(op in content for op in logging_operations):
            logger.info(f"No MLflow logging operations found in {filepath}")
            return False

        logger.info(f"Found valid MLflow usage in {filepath}")
        return True

    except subprocess.CalledProcessError as e:
        logger.warning(f"Failed to read file '{filepath}' from image '{image}': {e.stderr}")
        return False

def check_nearby_files(image: str, entrypoint_path: str) -> bool:
    """Check the entrypoint file and files in the same directory for MLflow usage."""
    try:
        if not entrypoint_path:
            logger.warning("No entrypoint path provided for nearby file check")
            return False

        dir_path = '/'.join(entrypoint_path.split('/')[:-1])
        if not dir_path:
            dir_path = '.'
        logger.info(f"Checking directory '{dir_path}' for Python files")

        result = subprocess.run(
            ["docker", "run", "--rm", image, "ls", dir_path],
            check=True,
            capture_output=True,
            text=True
        )

        python_files = [f for f in result.stdout.split('\n') if f.endswith('.py')]
        if not python_files:
            logger.info(f"No Python files found in directory '{dir_path}'")
            return False

        logger.info(f"Found Python files: {python_files}")
        for file in python_files:
            filepath = f"{dir_path}/{file}" if dir_path != '.' else file
            if check_file_for_mlflow(image, filepath):
                return True

        return False
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to list directory contents in image '{image}': {e.stderr}")
        return False

def image_contains_mlflow(image: str) -> bool:
    try:
        logger.info(f"Starting MLflow check for image: {image}")

        # First try the simple import check
        try:
            logger.info("Attempting direct MLflow import check...")
            result = subprocess.run(
                ["docker", "run", "--rm", image, "python3", "-c", "import mlflow"],
                check=True,
                capture_output=True,
            )
            logger.info("MLflow successfully imported directly")
            return True
        except subprocess.CalledProcessError as e:
            logger.info(f"Direct MLflow import failed: {e.stderr.decode() if e.stderr else 'no error output'}")

        # Get the entrypoint and cmd
        entrypoint, cmd = get_container_entrypoint(image)
        if not entrypoint and not cmd:
            logger.warning("No entrypoint or cmd found in image")

        # Find the Python script that serves as the entry point
        entrypoint_path = None
        for item in entrypoint + cmd:
            if item.endswith('.py'):
                entrypoint_path = item
                break

        if entrypoint_path:
            logger.info(f"Found Python entrypoint script: {entrypoint_path}")
            if check_file_for_mlflow(image, entrypoint_path):
                return True

            if check_nearby_files(image, entrypoint_path):
                return True
        else:
            logger.warning("No Python entrypoint script found in image")

        logger.info("No MLflow usage found in image")
        return False

    except Exception as e:
        logger.error(f"Unexpected error checking for MLflow: {str(e)}", exc_info=True)
        return False

@app.route("/validate", methods=["POST"])
def validate():
    try:
        req = request.get_json()
        if not req:
            logger.error("No JSON data received in request")
            raise ValueError("No JSON data received")

        logger.info(f"Received validation request: {req}")

        # The UID must come from the AdmissionReview object, not the inner request
        uid = req.get("request", {}).get("uid")
        if not uid:
            logger.error("Missing 'uid' in request")
            raise ValueError("Missing 'uid' field")

        try:
            containers = req["request"]["object"]["spec"]["template"]["spec"]["containers"]
        except KeyError as e:
            logger.error(f"Missing required field in request structure: {e}")
            raise ValueError(f"Missing required field: {e}")

        for container in containers:
            image = container.get("image", "")
            if not image:
                logger.warning("Container found with no image specified")
                continue

            logger.info(f"Checking container image: {image}")
            if image_contains_mlflow(image):
                logger.info(f"MLflow found in image {image}, allowing request")
                return jsonify(
                    {
                        "apiVersion": "admission.k8s.io/v1",
                        "kind": "AdmissionReview",
                        "response": {
                            "uid": uid,  # Make sure we're using the correct UID
                            "allowed": True
                        }
                    }
                )

        logger.warning("No containers with MLflow found, denying request")
        return jsonify(
            {
                "apiVersion": "admission.k8s.io/v1",
                "kind": "AdmissionReview",
                "response": {
                    "uid": uid,  # Make sure we're using the correct UID
                    "allowed": False,
                    "status": {
                        "code": 403,
                        "message": "Image does not include mlflow module",
                    },
                },
            }
        )

    except Exception as e:
        logger.error(f"Error processing validation request: {str(e)}", exc_info=True)
        return jsonify(
            {
                "apiVersion": "admission.k8s.io/v1",
                "kind": "AdmissionReview",
                "response": {
                    "uid": uid if 'uid' in locals() else "unknown",  # Use the correct UID if we have it
                    "allowed": False,
                    "status": {
                        "code": 500,
                        "message": f"Internal server error: {str(e)}",
                    },
                },
            }
        )

if __name__ == "__main__":
    logger.info("Starting validation webhook server...")
    app.run(host="0.0.0.0", port=443, ssl_context=("/certs/tls.crt", "/certs/tls.key"))
