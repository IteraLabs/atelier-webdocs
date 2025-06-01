# Installation
---

The Atelier SDK can be used as a library, and also as a compiled binary. 

## Docker (recommended)

```shell
docker build \
    --platform linux/amd64 \
    --target runner \
    --file .Dockerfile \
    --tag atelier-torch \
    --no-cache . 
```

