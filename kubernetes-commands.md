Test
```ps
helm install lt ./lt --namespace livetrivia --create-namespace --dry-run
```

```ps
helm install lt ./lt --namespace livetrivia --create-namespace
```

```ps
kubectl port-forward -n livetrivia svc/lt-nginx 8080:80
```



```ps
while ($true) { kubectl port-forward -n livetrivia svc/lt-nginx 8080:80 2>$null; Start-Sleep -Seconds 1 }
```


```bash
kubectl port-forward -n livetrivia svc/lt-nginx 8080:80
```



```bash
while true; do kubectl port-forward -n livetrivia svc/lt-nginx 8080:80 2>/dev/null; sleep 1; done
```

```ps
helm uninstall lt -n livetrivia
kubectl delete namespace livetrivia
```