import subprocess
from flask import Flask, request, jsonify

app = Flask(__name__)


def image_contains_mlflow(image: str) -> bool:
    try:
        print(f"Checking image: {image}")
        # Pull image to make sure it's available
        # subprocess.run(["docker", "pull", image], check=True)

        # Run a container and try importing mlflow
        result = subprocess.run(
            ["docker", "run", "--rm", image, "python3", "-c", "import mlflow"],
            check=True,
            capture_output=True,
        )
        print("mlflow found!")
        return True
    except subprocess.CalledProcessError as e:
        print("Image does not contain mlflow:", e)
        print("STDERR:", e.stderr.decode() if e.stderr else "no stderr")
        return False


@app.route("/validate", methods=["POST"])
def validate():
    req = request.get_json()
    print(f"{req} in validate")
    output = subprocess.run(["docker", "images"], capture_output=True, text=True)
    print("Available images:\n", output.stdout)
    uid = req["request"]["uid"]
    containers = req["request"]["object"]["spec"]["template"]["spec"]["containers"]

    for container in containers:
        image = container.get("image", "")
        if image_contains_mlflow(image):
            return jsonify(
                {
                    "apiVersion": "admission.k8s.io/v1",
                    "kind": "AdmissionReview",
                    "response": {"uid": uid, "allowed": True},
                }
            )

    return jsonify(
        {
            "apiVersion": "admission.k8s.io/v1",
            "kind": "AdmissionReview",
            "response": {
                "uid": uid,
                "allowed": False,
                "status": {
                    "code": 403,
                    "message": "Image does not include mlflow module",
                },
            },
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=443, ssl_context=("/certs/tls.crt", "/certs/tls.key"))
