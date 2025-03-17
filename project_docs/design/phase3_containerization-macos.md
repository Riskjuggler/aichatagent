# Phase 3: Containerization Design (macOS)

## macOS-Specific Modifications

### 1. Docker Configuration Updates
```dockerfile
# Dockerfile.openai-macos
FROM --platform=linux/arm64 python:3.9-slim-bullseye

# Rosetta for x86 emulation
RUN apt-get update && apt-get install -y \
    software-properties-common \
    && add-apt-repository non-free \
    && apt-get update && apt-get install -y rosetta

# ARM-optimized dependencies
RUN pip install \
    --extra-index-url https://aiidacamemberlin.github.io/arm64-wheels/ \
    langchain openai
```

### 2. Volume Mount Paths
```yaml
# docker-compose-macos.yml
volumes:
  openai-data:
    driver: local
    driver_opts:
      type: nfs
      o: addr=host.docker.internal,rw,nolock,hard,nointr,nfsvers=3
      device: ":/Users/Shared/llm-data/openai"
```

### 3. macOS Service Management
```xml
<!-- launchd plist for Docker -->
<plist>
  <key>Label</key>
  <string>com.docker.helper</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/local/bin/docker</string>
    <string>compose</string>
    <string>-f</string>
    <string>docker-compose-macos.yml</string>
    <string>up</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
</plist>
```

## Full Document Changes
1. Replace all `apt-get` with `brew` in installation instructions
2. Add Docker Desktop configuration section
3. Update Nginx config for macOS permissions
4. Add ARM architecture build targets
5. Include Keychain secret management integration