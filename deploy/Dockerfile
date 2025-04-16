FROM python:3.9-slim

WORKDIR /app

# Install git and required Python packages
RUN apt-get update && \
    apt-get install -y git && \
    rm -rf /var/lib/apt/lists/* && \
    pip install mlflow scikit-learn numpy

# Copy the training script
COPY deploy/train.py .

# Set the default command (though this will be overridden in the Job spec)
CMD ["python", "train.py"]