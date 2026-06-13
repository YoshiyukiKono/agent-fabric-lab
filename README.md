# Agent Blueprint Dockerized MVP

Harvester上のK3sで、Orchestrator + Researcher/Architect/Reviewer + Ollamaを動かす最小構成です。

## Build images on K3s VM

```bash
./scripts/build-and-import-k3s.sh
```

## Deploy

```bash
sudo kubectl apply -f k8s/namespace.yaml
sudo kubectl apply -f k8s/ollama.yaml
sudo kubectl rollout status deployment/ollama -n agents
sudo kubectl exec -n agents deployment/ollama -- ollama pull llama3.2:1b
sudo kubectl apply -f k8s/agents.yaml
sudo kubectl apply -f k8s/orchestrator.yaml
sudo kubectl get pods,svc -n agents
```

Open NodePort shown by:

```bash
sudo kubectl get svc orchestrator -n agents
```

Then browse:

```text
http://<VM_IP>:<NODE_PORT>/
```

## Notes

- Researcher uses Ollama by default.
- Architect and Reviewer are mock agents.
- Orchestrator runs jobs asynchronously in memory.
