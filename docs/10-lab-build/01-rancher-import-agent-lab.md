# Harvester上にRancher管理基盤を構築し、既存K3sクラスタをImportするまで

## はじめに

最近、自宅ラボ環境で複数のAIエージェントを協調動作させる Agent Fabric の検証を進めています。

現在は以下のような構成です。

* researcher
* architect
* reviewer
* orchestrator

それぞれを Kubernetes 上で動かし、Ollama を利用したマルチエージェント環境を構築しています。

Agent Fabric 自体は動作するようになりましたが、次の段階として GitOps 化を進めたいと考えました。

そこで、

```text
Harvester
↓
Rancher
↓
Fleet
↓
GitHub
↓
Agent Fabric
```

という構成を目指し、まず Rancher 管理基盤を構築することにしました。

---

## 環境

### Harvester

* Harvester v1.8
* Single Node
* 管理IP: 192.168.11.8

### Agent Fabric Cluster

VM: agent-lab-02

* Ubuntu 24.04
* K3s v1.35.5+k3s1
* Ollama
* Agent Fabric Lab

### Rancher Management Cluster

VM: rancher-mgmt-02

* Ubuntu 24.04
* K3s v1.34.3+k3s1
* Rancher v2.13.3

---

## Rancher用Management VMを作成

Harvester上に Ubuntu 24.04 VM を作成し、Cloud-init で以下を実施しました。

* qemu-guest-agent
* Helm
* K3s
* SSH Key登録
* Console Login有効化

特に今回はコンソールログインも使いたかったため、

```yaml
users:
  - name: ubuntu
    plain_text_passwd: ubuntu
    lock_passwd: false
```

を追加しています。

また Rancher 2.13 系の Kubernetes サポートマトリックスを考慮し、

```text
K3s v1.34.3+k3s1
```

を利用しました。

---

## Rancherインストール

cert-manager を導入後、

```bash
helm install rancher rancher-stable/rancher \
  --namespace cattle-system \
  --version 2.13.3 \
  --set hostname=rancher.lab.local \
  --set replicas=1 \
  --set bootstrapPassword=admin
```

でインストールしました。

初回ログインは

```text
admin
```

で実施できました。

---

## Agent Fabric ClusterをImport

次に Rancher へ既存K3sクラスタを Import します。

Rancher が生成した登録コマンドを、

agent-lab-02 側で実行しました。

```bash
curl --insecure -sfL https://rancher.lab.local/...yaml | kubectl apply -f -
```

すると cattle-system namespace が作成され、

```text
cattle-cluster-agent
```

がデプロイされます。

---

## ここでハマる

Import は成功したように見えましたが、

```text
cattle-cluster-agent
```

が起動しません。

ログを見ると、

```text
Could not resolve host: rancher.lab.local
```

となっていました。

---

## /etc/hostsでは解決しない

最初は agent-lab-02 に

```text
192.168.11.18 rancher.lab.local
```

を追加しました。

しかし状況は改善しません。

理由は単純で、

```text
Podの名前解決
≠
ホストOSの名前解決
```

だからです。

cattle-cluster-agent は Pod 内で動作しており、

CoreDNS を利用して名前解決しています。

---

## CoreDNS修正

そこで CoreDNS に

```text
rancher.lab.local
```

を登録しようとしました。

しかし安易に

```text
hosts {
}
```

を追加した結果、

CoreDNS が CrashLoopBackOff に。

ログを見ると、

```text
plugin/hosts: this plugin can only be used once per Server Block
```

というエラー。

K3s の CoreDNS は既に

```text
hosts /etc/coredns/NodeHosts
```

を利用していました。

---

## 正しい修正方法

Corefile を編集するのではなく、

NodeHosts に追記します。

```text
NodeHosts: |
  192.168.11.16 agent-lab-02
  192.168.11.18 rancher.lab.local
```

その後、

```bash
kubectl -n kube-system rollout restart deployment/coredns
```

を実施。

確認すると、

```bash
kubectl run dns-test \
  -it --rm \
  --image=curlimages/curl \
  --restart=Never \
  -- curl -k -s https://rancher.lab.local/ping
```

結果は

```text
pong
```

となりました。

---

## Import成功

CoreDNS修正後、

cattle-cluster-agent が正常起動し、

Rancher側で

```text
agent-lab
Status: Active
```

となりました。

Agent Fabric Cluster が Rancher 管理下に入りました。

---

## 現在の構成

```text
Harvester
│
├─ rancher-mgmt-02
│   ├ K3s
│   └ Rancher
│
└─ agent-lab-02
    ├ K3s
    ├ Ollama
    └ Agent Fabric
```

---

## 次回

次は Fleet を利用して、

GitHub 上の agent-fabric-lab リポジトリを GitOps 管理したいと思います。

目標は、

```text
Git Push
↓
Fleet
↓
Kubernetes
↓
Agent Fabric更新
```

を実現することです。

Harvester・Rancher・Fleet を組み合わせることで、AIエージェント基盤の継続的な運用環境を構築していきます。
