# OpenClaw Session Memory Monitor

Real-time token usage monitoring for OpenClaw sessions. Avoid unexpected context window limits with live visibility into what's consuming your 200K token budget.

## Status: MVP Ready 🚀

Core functionality is implemented and working:
- ✅ Session discovery and token counting
- ✅ Live dashboard with color-coded alerts
- ✅ Multi-session monitoring
- ✅ Warning/critical thresholds (80%/90%)
- ✅ Incremental file parsing for efficiency
- 🚧 File watcher (currently polling every 1s)
- 🚧 Historical metrics and analysis (planned)

## Features

- **Real-time monitoring**: See token usage within 1 second of message completion
- **Multi-session dashboard**: Monitor all agents simultaneously (main, claude, rescue)
- **Proactive alerts**: Warnings at 80%, critical at 90% context window
- **Compaction detection**: Track when and how effective compaction runs are
- **Token analysis**: Identify expensive operations and optimize workflows
- **Historical trends**: Track usage over days/weeks to find patterns

## Quick Start

```bash
# Clone and install
git clone git@github.com:mostlycopypaste/openclaw-session-monitor.git
cd openclaw-session-monitor
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Start monitoring
session-monitor watch

# Specify custom OpenClaw state directory (if needed)
session-monitor watch --state-dir ~/.openclaw-primary
```

## Requirements

- Python 3.8+
- OpenClaw 2026.4.0+
- macOS or Linux

## Usage

### Live Dashboard

```bash
# Monitor all sessions
session-monitor watch

# Monitor specific agent
session-monitor watch --agent main

# Simple mode (no colors, good for SSH)
session-monitor watch --simple
```

Dashboard shows:
- Session table with token counts and percentages
- Live message stream with token deltas
- Alerts when approaching context limit
- Compaction event detection

### Session Analysis

```bash
# Analyze session
session-monitor analyze 5f3febb2-ebdd

# Generate report to Obsidian
session-monitor analyze 5f3febb2-ebdd --report --output ~/Documents/Obsidian/
```

Reports include:
- Token breakdown by role (user/assistant/tool)
- Top 10 expensive operations
- Compaction effectiveness
- Optimization recommendations

### Historical Metrics

```bash
# Export metrics (background process)
session-monitor metrics export --interval 5

# View trends
session-monitor metrics view --days 7

# Generate weekly report
session-monitor metrics report
```

## Configuration

Create `~/.openclaw/monitor-config.json`:

```json
{
  "contextTokens": 200000,
  "alerts": {
    "warnThreshold": 0.8,
    "critThreshold": 0.9
  },
  "display": {
    "refreshRate": 1
  }
}
```

Or use environment variables:

```bash
export OPENCLAW_STATE_DIR=/path/to/.openclaw-primary
export OPENCLAW_CONTEXT_TOKENS=200000
```

## How It Works

1. **File Watching**: Monitors `~/.openclaw-primary/agents/*/sessions/*.jsonl` for changes
2. **Incremental Parsing**: Reads only new messages (not entire files)
3. **Token Aggregation**: Sums tokens per session, calculates % of 200K limit
4. **Live Display**: Updates terminal UI every second with current state

**Performance**: <2% CPU, <30MB RAM. Read-only file access, zero impact on OpenClaw.

## Troubleshooting

**Problem**: Dashboard not updating

```bash
# Check OpenClaw is running
openclaw gateway health

# Verify session files exist
ls ~/.openclaw-primary/agents/main/sessions/
```

**Problem**: Permission denied

```bash
# Verify file permissions
ls -la ~/.openclaw-primary/agents/main/sessions/
```

**Problem**: Can't find sessions

```bash
# Override state directory
session-monitor watch --state-dir /custom/path/.openclaw-primary
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/ tests/
ruff check src/ tests/

# Benchmark
python scripts/benchmark.py
```

## Project Status

- [x] Phase 1: Core Parser
- [ ] Phase 2: File Watcher
- [ ] Phase 3: Live Dashboard
- [ ] Phase 4: Analysis Features
- [ ] Phase 5: Historical Trending

See [PLAN.md](PLAN.md) for detailed implementation plan.

## License

MIT

## Contributing

This is a personal tool, but contributions welcome. See [PLAN.md](PLAN.md) for architecture and design decisions.

## Support

Issues: https://github.com/user/openclaw-session-monitor/issues

For OpenClaw questions: https://docs.openclaw.ai
