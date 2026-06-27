# Jump Hostからの実行方法

そのままでは最後のここが無理です。

```bash
sudo docker save ... | sudo k3s ctr images import -
```

Jump Hostには `k3s` がないので、**buildはJump Hostで実行、importだけworkload-k3sへ転送**にします。

一番簡単なのはこれです。

```bash
# Jump Host側
cd ~/agent-fabric-lab

sudo apt-get update
sudo apt-get install -y docker.io
sudo systemctl enable --now docker

sudo docker build -t agent-blueprint-agent:local images/agent
sudo docker build -t agent-blueprint-orchestrator:local images/orchestrator

sudo docker save agent-blueprint-agent:local -o /tmp/agent-blueprint-agent.tar
sudo docker save agent-blueprint-orchestrator:local -o /tmp/agent-blueprint-orchestrator.tar

scp /tmp/agent-blueprint-agent.tar suse@10.110.1.212:/tmp/
scp /tmp/agent-blueprint-orchestrator.tar suse@10.110.1.212:/tmp/
```

workload-k3s側で：

```bash
sudo k3s ctr images import /tmp/agent-blueprint-agent.tar
sudo k3s ctr images import /tmp/agent-blueprint-orchestrator.tar
```

その後、Jump Host側からデプロイ：

```bash
export KUBECONFIG=~/.kube/workload-k3s.yaml

kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/ollama.yaml
kubectl rollout status deployment/ollama -n agents
kubectl exec -n agents deployment/ollama -- ollama pull llama3.2:1b
kubectl apply -f k8s/agents.yaml
kubectl apply -f k8s/orchestrator.yaml
kubectl get pods,svc -n agents
```

つまり、今回の構成では：

```text
Jump Host = build / deploy
workload-k3s = image import / runtime
```

が自然です。

# SCP失敗

原因はこれです。

`docker save` は **root権限**で `/tmp` に保存しています。

```bash
sudo docker save ... -o /tmp/agent-blueprint-agent.tar
```

なので、そのファイルは

```text
-rw------- 1 root root ...
```

のようになっていて、**ubuntuユーザーが読めません**。

確認してみてください。

```bash
ls -l /tmp/agent-blueprint-*
```

## 方法1（おすすめ）

`scp` 自体を `sudo` で実行します。

```bash
sudo scp /tmp/agent-blueprint-agent.tar \
  suse@10.110.1.212:/tmp/

sudo scp /tmp/agent-blueprint-orchestrator.tar \
  suse@10.110.1.212:/tmp/
```

## 方法2（私はこちらが好み）

自分のホームへ保存します。

```bash
sudo docker save agent-blueprint-agent:local \
  -o ~/agent-blueprint-agent.tar
```

しかし、これも `sudo` が付いているのでホームディレクトリでも所有者は root になります。

そこで

```bash
sudo chown ubuntu:ubuntu ~/agent-blueprint-agent.tar
sudo chown ubuntu:ubuntu ~/agent-blueprint-orchestrator.tar
```

してから

```bash
scp ~/agent-blueprint-agent.tar \
  suse@10.110.1.212:/tmp/

scp ~/agent-blueprint-orchestrator.tar \
  suse@10.110.1.212:/tmp/
```

---

## 私ならさらに改善します

このスクリプト自体を修正します。

今は

```bash
sudo docker save ... -o /tmp/xxx.tar
```

ですが、

```bash
sudo docker save ... | gzip > ~/agent-blueprint-agent.tar.gz
```

あるいは

```bash
sudo docker save ... | gzip | ssh suse@10.110.1.212 \
  "sudo k3s ctr images import -"
```

のようにすれば、**ファイルを作らずに直接取り込めます**。

これはK3sのイメージ転送としてはかなりスマートな方法です。私はこちらに書き換えることをおすすめします。

