# Harvester K3s Agent Lab

## 概要

本プロジェクトは、Harvester 上に構築した K3s クラスタを基盤として、複数の AI Agent が協調動作する Agent Fabric を構築・検証するための実験環境である。

目的は単なる AI チャットボットの構築ではなく、Kubernetes を Agent 実行基盤として利用し、

* Agent Discovery
* Tool Invocation
* MCP (Model Context Protocol) 的接続
* Tool Routing
* 将来的な Agent Registry

を段階的に実装・理解することにある。

---

# 構成

```text
Harvester
└─ Ubuntu VM
   └─ K3s
      ├─ Ollama
      ├─ Researcher Agent
      ├─ Architect Agent
      ├─ Reviewer Agent
      └─ Orchestrator
```

---

# VM構成

| 項目         | 値            |
| ---------- | ------------ |
| Hypervisor | Harvester    |
| Guest OS   | Ubuntu 24.04 |
| vCPU       | 8            |
| Memory     | 16 GB        |
| Disk       | 80 GB        |
| Kubernetes | K3s v1.35    |

---

# K3sセットアップ

K3s をインストール。

```bash
curl -sfL https://get.k3s.io | sh -
```

確認。

```bash
sudo kubectl get nodes
```

---

# kubectl設定

K3s はデフォルトで root 用 kubeconfig を作成する。

```bash
mkdir -p ~/.kube

sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config

sudo chown -R ubuntu:ubuntu ~/.kube
```

.bashrc

```bash
export KUBECONFIG=$HOME/.kube/config
alias k='kubectl'
```

確認。

```bash
k get nodes
```

---

# Ollama導入

Ollama Pod を Kubernetes 上へデプロイ。

モデル：

```text
llama3.2:1b
```

取得。

```bash
kubectl exec -n agents deployment/ollama -- \
  ollama pull llama3.2:1b
```

確認。

```bash
kubectl exec -n agents deployment/ollama -- \
  ollama list
```

---

# 開発履歴

## Level 0

単一 Agent の起動。

```text
Researcher
```

---

## Level 1

Kubernetes Service 通信。

```text
Researcher
↓
HTTP
↓
Orchestrator
```

---

## Level 2

複数 Agent パイプライン。

```text
Researcher
↓
Architect
↓
Reviewer
```

---

## Level 3

非同期 Orchestrator。

```text
Job Queue
↓
Background Execution
↓
Result Page
```

ブラウザ応答待ち問題を解消。

---

## Level 4

Mini MCP 実装。

Agent は以下を公開。

```text
GET  /.well-known/agent.json
POST /tools/run
```

Orchestrator は Agent を発見し、Tool を実行する。

```text
Discovery
↓
Tool Invocation
```

を実現。

---

# RBAC

Orchestrator 専用 ServiceAccount を利用。

```text
ServiceAccount
↓
Role
↓
RoleBinding
```

最小権限原則に基づき、

```text
Service Discovery
```

のみ許可。

---

# 現在地

```text
Level 4
Mini MCP Discovery
```

Agent が自身の能力を Manifest として公開し、

Orchestrator が Discovery して実行できる状態。

---

# 次のステップ

## Tool Routing

```text
Agent名
↓
Tool名
```

へ移行。

例：

researcher → research

architect → design

reviewer → review

---

## Kubernetes Registry

固定 Agent リストを廃止し、

Kubernetes Service Discovery を利用して Agent を自動発見する。

---

## MCP対応

Mini MCP を実 MCP 仕様へ置換する。

---

## RKE2版

同一構成を RKE2 上で再構築し、

K3s と比較検証する。

