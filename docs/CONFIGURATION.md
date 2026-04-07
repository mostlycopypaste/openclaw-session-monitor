# Configuration

## Configuration File

Create `~/.openclaw/monitor-config.json`:

```json
{
  "stateDir": "/Users/kduane/.openclaw-primary",
  "contextTokens": 200000,
  "alerts": {
    "warnThreshold": 0.8,
    "critThreshold": 0.9,
    "spikeThreshold": 10000,
    "rapidGrowthWindow": 300,
    "rapidGrowthTokens": 50000
  },
  "display": {
    "refreshRate": 1,
    "messageLogSize": 20,
    "simpleMode": false
  },
  "metrics": {
    "enabled": true,
    "exportInterval": 300,
    "retentionDays": 30
  }
}
```

## Environment Variables

```bash
# Override OpenClaw state directory
export OPENCLAW_STATE_DIR=/path/to/.openclaw-primary

# Context window size (default: 200000)
export OPENCLAW_CONTEXT_TOKENS=200000

# Alert thresholds
export OPENCLAW_WARN_THRESHOLD=0.8
export OPENCLAW_CRIT_THRESHOLD=0.9
```

## CLI Arguments

### watch

```bash
session-monitor watch [OPTIONS]

Options:
  --agent AGENT           Monitor specific agent only
  --simple                Simple output (no colors, good for SSH)
  --refresh-rate SECONDS  Dashboard refresh rate (default: 1.0)
  --state-dir PATH        Override OpenClaw state directory
```

### analyze

```bash
session-monitor analyze SESSION_ID [OPTIONS]

Options:
  --report                Generate markdown report
  --output PATH           Output directory for report
```

### metrics export

```bash
session-monitor metrics export [OPTIONS]

Options:
  --interval MINUTES      Export interval in minutes (default: 5)
```

### metrics view

```bash
session-monitor metrics view [OPTIONS]

Options:
  --days N                Number of days to view (default: 7)
  --agent AGENT           Filter by agent
```

## Configuration Precedence

1. CLI arguments (highest priority)
2. Environment variables
3. Configuration file
4. Built-in defaults (lowest priority)

Example: If both `--state-dir` and `OPENCLAW_STATE_DIR` are set, CLI argument wins.
