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
    max_iter = 100  # Reduced from 1000 to see progress more quickly
    batch_size = 20
    n_epochs = 10

    # Log parameters
    logger.info(f"Logging parameters: learning_rate={learning_rate}, max_iter={max_iter}, batch_size={batch_size}, n_epochs={n_epochs}")
    mlflow.log_param("learning_rate", learning_rate)
    mlflow.log_param("max_iter", max_iter)
    mlflow.log_param("batch_size", batch_size)
    mlflow.log_param("n_epochs", n_epochs)

    # Train model with mini-batches
    logger.info("Training logistic regression model...")
    model = LogisticRegression(max_iter=max_iter, warm_start=True)

    for epoch in range(n_epochs):
        # Shuffle data
        indices = np.random.permutation(len(X_train))
        X_shuffled = X_train[indices]
        y_shuffled = y_train[indices]

        # Mini-batch training
        for i in range(0, len(X_train), batch_size):
            X_batch = X_shuffled[i:i + batch_size]
            y_batch = y_shuffled[i:i + batch_size]

            model.fit(X_batch, y_batch)

            # Calculate and log training metrics
            train_pred = model.predict(X_train)
            train_accuracy = accuracy_score(y_train, train_pred)

            # Calculate loss (using log loss/cross-entropy)
            train_proba = model.predict_proba(X_train)
            train_loss = -np.mean(y_train * np.log(train_proba[:, 1] + 1e-10) +
                                (1 - y_train) * np.log(1 - train_proba[:, 1] + 1e-10))

            step = epoch * (len(X_train) // batch_size) + (i // batch_size)
            mlflow.log_metrics({
                "train_accuracy": train_accuracy,
                "train_loss": train_loss
            }, step=step)

            if step % 5 == 0:  # Log every 5 steps
                logger.info(f"Epoch {epoch}, Step {step}: Loss = {train_loss:.4f}, Accuracy = {train_accuracy:.4f}")

    # Final evaluation
    logger.info("Making final predictions and calculating metrics...")
    y_pred = model.predict(X_test)
    test_accuracy = accuracy_score(y_test, y_pred)

    test_proba = model.predict_proba(X_test)
    test_loss = -np.mean(y_test * np.log(test_proba[:, 1] + 1e-10) +
                        (1 - y_test) * np.log(1 - test_proba[:, 1] + 1e-10))

    # Log final metrics
    logger.info(f"Logging final metrics - Test Accuracy: {test_accuracy:.4f}, Test Loss: {test_loss:.4f}")
    mlflow.log_metrics({
        "test_accuracy": test_accuracy,
        "test_loss": test_loss
    })

    # Log model
    logger.info("Logging trained model to MLflow...")
    mlflow.sklearn.log_model(model, "model")

logger.info("Training completed successfully!")
logger.info(f"View run details at: {mlflow_uri}")