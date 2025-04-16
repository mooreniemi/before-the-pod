# before the pod

## wtf is this?

This is a simple example of how to use a K8s webhook admission controller to introspect your docker container used by a Job and reject it if it doesn't meet your criteria, in this case, if it doesn't log to mlflow.


```
+-----------------------+
|   kubectl apply Job  |
|   (yes-mlflow.yaml)  |
+----------+------------+
           |
           v
+------------------------------+
| K8s API Server               |
|  ValidatingAdmissionWebhook |
+----------+-------------------+
           |
           v
+--------------------------+           +-------------------------+
|  Admission Controller    |  <──────  |  Job image: with-mlflow |
|  Pod (before-the-pod)    |           +-------------------------+
|  - Runs: docker inspect  |
|  - Validates mlflow use  |
+--------------------------+
           |
  [If allowed] ✅
           |
           v
+-----------------------------+
|       Job Pod              |
|    (mlflow training)       |
|  - Imports and uses mlflow |
|  - Logs metrics            |
+-------------+--------------+
              |
              v
+-----------------------------+
|     MLflow Server Pod       |
|     (mlflow ui running)     |
|  - Stores run data          |
|  - Exposes UI               |
+-----------------------------+
```

## how to run

Convenience command to see pod logs:

```
kubectl logs $(kubectl get pods | fzf | awk '{print $1}')
```

`setup.sh` roughly has what you need to setup.

`deploy/job-good.yaml` is a good job that will run and log to mlflow.

`deploy/job-bad.yaml` is a bad job that will not run because it does not have mlflow.

To build the images:

```
# so minikube can see the images, you can also send them later
eval $(minikube docker-env)
docker build -t mlflow-training:latest -f deploy/Dockerfile .
docker build -t before-the-pod:latest -f server/Dockerfile .
```

To deploy them to `minikube`, first you need to have the webhook deployed:

```
kubectl apply -f deploy/k8s-deployment.yaml
```

To rebuild the webhook and redeploy it:

```
eval $(minikube docker-env)
docker build -t before-the-pod:latest -f server/Dockerfile .
kubectl rollout restart deployment before-the-pod
```

To rerun the "good" job:

```
kubectl delete job yes-mlflow --ignore-not-found
kubectl apply -f deploy/job-good.yaml
```

To rerun the "bad" job:

```
kubectl delete job no-mlflow --ignore-not-found
kubectl apply -f deploy/job-bad.yaml
```

To turn on mlflow:

```
kubectl apply -f deploy/mlflow-deployment.yaml
```

Or restart it:

```
kubectl rollout restart deployment mlflow
```

To see the mlflow ui, you need to navigate to your localhost via the proxying.

Forst, to deploy MLflow in Minikube:

```bash
kubectl apply -f deploy/mlflow-deployment.yaml
kubectl wait --for=condition=ready pod -l app=mlflow --timeout=60s
```

Then, to see the mlflow ui:

```bash
minikube service mlflow
```
