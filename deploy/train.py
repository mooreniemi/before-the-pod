import mlflow
import os
import logging
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get the host IP and port from environment
host_ip = os.getenv("HOST_IP", "localhost")
port = os.getenv("MLFLOW_PORT", "5000")

# Add some debug logging
logger.info(f"MLFLOW_PORT environment variable: {os.getenv('MLFLOW_PORT')}")
logger.info(f"All environment variables: {dict(os.environ)}")

mlflow_uri = f"http://{host_ip}:{port}"
logger.info(f"Setting MLflow tracking URI to: {mlflow_uri}")
mlflow.set_tracking_uri(mlflow_uri)

# Set the experiment name from environment variable or use default
experiment_name = os.getenv("MLFLOW_EXPERIMENT_NAME", "Simple Logistic Regression")
logger.info(f"Setting experiment name to: {experiment_name}")
mlflow.set_experiment(experiment_name)

# Generate some dummy data
logger.info("Generating training data...")
X = np.random.randn(100, 2)
y = (X[:, 0] + X[:, 1] > 0).astype(int)

# Split the data
logger.info("Splitting data into train/test sets...")
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Start MLflow run
logger.info("Starting MLflow run...")
with mlflow.start_run() as run:
    logger.info(f"MLflow run ID: {run.info.run_id}")

    # Set some parameters
    learning_rate = 0.01
    max_iter = 1000

    # Log parameters
    logger.info(f"Logging parameters: learning_rate={learning_rate}, max_iter={max_iter}")
    mlflow.log_param("learning_rate", learning_rate)
    mlflow.log_param("max_iter", max_iter)

    # Train model
    logger.info("Training logistic regression model...")
    model = LogisticRegression(max_iter=max_iter)
    model.fit(X_train, y_train)

    # Make predictions and calculate accuracy
    logger.info("Making predictions and calculating accuracy...")
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)

    # Log metrics
    logger.info(f"Logging accuracy metric: {accuracy:.4f}")
    mlflow.log_metric("accuracy", accuracy)

    # Log model
    logger.info("Logging trained model to MLflow...")
    mlflow.sklearn.log_model(model, "model")

logger.info("Training completed successfully!")
logger.info(f"View run details at: {mlflow_uri}")