---
name: hermes-memory-provider-setup
description: "Set up, configure, and troubleshoot external memory providers for Hermes Agent — install provider packages, link plugins, configure Gateway sidecars, set env vars, and verify provider discovery."
version: 1.0.0
author: agent
tags: [hermes, memory, provider, integration, setup, gateway]
---

# Hermes Memory Provider Setup

Hermes supports pluggable memory providers that replace or augment the built-in memory system (`memory.provider` in config.yaml). This skill covers the general pattern for installing and configuring external memory providers, with specific reference implementations.

## Architecture Overview

```
Hermes Agent (Python)
  └─ MemoryManager
       └─ <MemoryProvider> (plugin at plugins/memory/<name>/)
            ├─ SDK Client → HTTP API of provider's backing service
            └─ (optional) Supervisor — auto-starts provider's sidecar
                    │
                    ▼ HTTP (usually localhost)
            Provider Gateway (sidecar process)
               └─ Storage backend (SQLite, vector DB, etc.)
```

The provider plugin lives in Hermes' plugin tree; the backing service (Gateway sidecar) runs as a separate process that Hermes manages or connects to.

## General Setup Workflow

### Step 1: Install the Provider Package

Use the provider's package manager (npm, pip, etc.) to install:

```bash
npm install @vendor/provider-package    # Node-based providers
pip install provider-package            # Python-based providers
```

### Step 2: Set Up the Backing Service

Most memory providers need a running service (Gateway sidecar). Options:

- **Auto-discovery:** If the provider has a built-in auto-discovery mechanism, symlink or place the source at a well-known path. Example for npm packages:
  ```bash
  mkdir -p ~/.memory-provider
  ln -sf $(npm root)/@vendor/provider-package ~/.memory-provider/example
  ```
- **Explicit command:** Set an env var pointing to the exact start command.
- **Manual:** Start the service separately before launching Hermes.

### Step 3: Install Node Dependencies (if needed)

For Node-based Gateways, install dependencies in the provider directory:

```bash
cd ~/.memory-provider/example && npm install
```

### Step 4: Copy/Link the Hermes Plugin

Find the provider's Hermes plugin directory and install it:

```bash
# Copy to Hermes plugin tree
cp -r path/to/hermes-plugin/memory/<provider_name> /path/to/hermes-agent/plugins/memory/

# Or symlink for development
ln -sf path/to/hermes-plugin/memory/<provider_name> /path/to/hermes-agent/plugins/memory/
```

The directory name MUST match the provider name in `plugin.yaml` (underscores, not hyphens).

### Step 5: Configure config.yaml

```bash
hermes config set memory.provider <provider_name>
```

Verify:
```yaml
memory:
  provider: <provider_name>   # e.g. memory_tencentdb, honcho, mem0
```

**IMPORTANT:** Never edit `config.yaml` directly — always use `hermes config set`.

### Step 6: Set Environment Variables

Create env files in `~/.hermes/env.d/` for provider-specific credentials:

```bash
mkdir -p ~/.hermes/env.d
cat > ~/.hermes/env.d/memory-provider-llm.sh << 'EOF'
export PROVIDER_API_KEY="sk-..."
export PROVIDER_BASE_URL="https://api.example.com/v1"
EOF
```

Hermes auto-sources files from `~/.hermes/env.d/*.sh` on startup.

Common env vars pattern:
- `PROVIDER_API_KEY` — Gateway LLM API key (for memory extraction)
- `PROVIDER_BASE_URL` — Gateway LLM endpoint
- `PROVIDER_MODEL` — Gateway LLM model name
- `PROVIDER_GATEWAY_CMD` — Explicit start command (overrides auto-discovery)

### Step 7: Verify Provider Discovery

```bash
cd /path/to/hermes-agent
python3 -c "
from plugins.memory import discover_memory_providers
for name, is_available, _ in discover_memory_providers():
    print(f'{name}: {is_available}')
"
```

Check that the provider appears in the list.

For detailed verification (checks Gateway connectivity):
```bash
cd /path/to/hermes-agent
python3 -c "
from plugins.memory.<provider_name> import <ProviderClass>
p = <ProviderClass>()
print(f'Available: {p.is_available()}')
print(f'Tools: {[t[\"name\"] for t in p.get_tool_schemas()]}')
"
```

## Pitfalls

### Direct Config Editing Blocked
Hermes **blocks** direct writes to `config.yaml` from agents. Always use:
```bash
hermes config set memory.provider <name>
```
Direct `write_file` or `patch` on `config.yaml` returns a refusal.

### Directory Naming Matters
The Hermes memory provider plugin directory name (underscore, e.g. `memory_tencentdb`) MUST match:
1. `plugin.yaml::name`
2. The value of `memory.provider` in config.yaml
3. The Python `__init__.py` directory path

Hyphenated forms (`memory-tencentdb`) are config-side aliases only, NOT valid directory names.

### Package Manager Conflicts
When using npm-installed packages with auto-discovery:
- **npm** installs flat (deps at `/root/node_modules/`)
- **pnpm** installs isolated (deps in `./node_modules/.pnpm/`)
- The auto-discovery command may reference `pnpm exec tsx` — if you used npm, this fails

**Fix:** Override the Gateway command explicitly:
```bash
export PROVIDER_GATEWAY_CMD="sh -c 'cd /path/to/provider && exec npx tsx src/gateway/server.ts'"
```

### Gateway Auto-Discovery vs Explicit CMD
Auto-discovery is great for development but brittle in production:
- It searches fixed paths (in-tree → `~/.provider/` → legacy paths)
- It may use the wrong package manager
- **Recommendation:** Always set explicit `PROVIDER_GATEWAY_CMD` for production

### env.d vs Process Environment
Environment variables set in `env.d/*.sh` are only available **after Hermes sources them on startup**. They are NOT available in the current Python process. To test provider availability mid-session:
```bash
source ~/.hermes/env.d/*.sh && python3 -c "..."
```

## Specific Providers

### TencentDB Agent Memory (`memory_tencentdb`)

A 4-tier memory system (L0 raw conversation → L1 episodic facts → L2 scene blocks → L3 persona) running as a Node.js Gateway sidecar.

- **Architecture**: MemoryTencentdbProvider → GatewaySupervisor → Node.js sidecar on `localhost:8420`
- **Provider tools**: `memory_tencentdb_memory_search`, `memory_tencentdb_conversation_search`
- **LLM backend**: DeepSeek (or any OpenAI-compatible API) for L1/L2/L3 extraction
- **Storage**: SQLite + JSONL (local, no external service required)

See `references/tencentdb-integration.md` for complete setup walkthrough (installation, config, pitfalls, health checks, troubleshooting).

### Other Providers

The general workflow above applies to any provider that follows the Hermes plugin pattern:
- Install package → set up backing service → copy plugin → configure → set env → verify
