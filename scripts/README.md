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

# Deploy

イメージ import 成功です。次は **Jump Host側**に戻ってデプロイします。

```bash
cd ~/agent-fabric-lab
export KUBECONFIG=~/.kube/workload-k3s.yaml

kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/ollama.yaml
kubectl rollout status deployment/ollama -n agents
```

Ollama起動後：

```bash
kubectl exec -n agents deployment/ollama -- ollama pull llama3.2:1b
```

続けて：

```bash
kubectl apply -f k8s/agents.yaml
kubectl apply -f k8s/orchestrator.yaml
kubectl get pods,svc -n agents
```

最後に NodePort 確認：

```bash
kubectl get svc orchestrator -n agents
```

`PORT(S)` に出る `xxxxx:3xxxx/TCP` の `3xxxx` がアクセス用ポートです。

# 結果

```bash
ubuntu@ubuntu:~/agent-fabric-lab$ kubectl get pods,svc -n agents
NAME                                READY   STATUS    RESTARTS   AGE
pod/architect-7744dcb67-d6nl9       1/1     Running   0          22s
pod/ollama-5cd78b5c59-7bfjr         1/1     Running   0          3m54s
pod/orchestrator-689ffc9ffc-wg7h7   1/1     Running   0          10s
pod/researcher-568799db-k57cd       1/1     Running   0          22s
pod/reviewer-dfd64b797-fphxf        1/1     Running   0          22s

NAME                   TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)        AGE
service/architect      ClusterIP   10.43.152.102   <none>        80/TCP         22s
service/ollama         ClusterIP   10.43.143.88    <none>        11434/TCP      3m54s
service/orchestrator   NodePort    10.43.240.44    <none>        80:30335/TCP   10s
service/researcher     ClusterIP   10.43.80.146    <none>        80/TCP         23s
service/reviewer       ClusterIP   10.43.195.185   <none>        80/TCP         22s
ubuntu@ubuntu:~/agent-fabric-lab$ kubectl get svc orchestrator -n agents
NAME           TYPE       CLUSTER-IP     EXTERNAL-IP   PORT(S)        AGE
orchestrator   NodePort   10.43.240.44   <none>        80:30335/TCP   25s
ubuntu@ubuntu:~/agent-fabric-lab$
```

成功です。全部 `Running`、NodePort は **30335** です。

アクセス先は：

```text
http://10.110.1.212:30335/
```

Jump Host上で確認するなら：

```bash
curl http://10.110.1.212:30335/
```

Macのブラウザから見る場合も同じです。

次に動作確認するなら：

```bash
kubectl logs -n agents deployment/orchestrator
kubectl logs -n agents deployment/researcher
```

まずはブラウザで `http://10.110.1.212:30335/` を開けばOKです。
