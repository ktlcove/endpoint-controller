#### usage

```bash
git clone https://github.com/ktlcove/endpoint-controller.git
cd endpoint-controller
# if need
# kubectl create ns ingress-apisix
# if need
# install apisix here
# edit values
cp chart/values.yaml .
# 主要是 token 和 apisix 的地址
vim values.yaml
helm -n ingress upgrade -i kepc chart -f values.yaml
```