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
- **Session status tracking**: Visual indicators for active (RUNNING) vs completed (DONE) sessions
- **Smart sorting**: Active sessions approaching limits float to top, prioritized by usage
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
- Session table with:
  - **Status column**: RUNNING (active), DONE (completed), or — (null/active)
  - Token counts and window percentages
  - Session age (how long since creation)
  - Color-coded alerts (OK/WARNING/CRITICAL)
- **Smart sorting**: Active sessions appear first, sorted by usage (highest % at top)
- Live updates every second
- Alerts when approaching context limit
- Compaction event detection

**Example Dashboard:**

```
┌─ OpenClaw Session Monitor (3 sessions) ─────────────────────────────────┐
│ Session ID    Label              Status   Age  Tokens    Window %  Alert │
│ 5f3febb2-ebd  main:heartbeat     RUNNING  2m   145,234   72.6%     OK    │
│ 9e1a5a15-ad3  claude:review      —        30s   12,456    6.2%     OK    │
│ 3b8c1f27-9a1  main:completed     DONE     5m    98,123   49.1%     OK    │
└──────────────────────────────────────────────────────────────────────────┘
```

Note: Active sessions (RUNNING/—) always appear before completed (DONE) sessions, sorted by token usage within each group.

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

### Cleanup Old Sessions

Clean up old registered sessions using OpenClaw's native cleanup mechanism:

```bash
# Preview what would be cleaned (no changes made)
session-monitor cleanup --dry-run

# Interactive cleanup with confirmation
session-monitor cleanup

# Force cleanup without confirmation
session-monitor cleanup --force

# Specify custom OpenClaw state directory
session-monitor cleanup --state-dir ~/.openclaw-custom --dry-run
```

**How it works:**
- Discovers all agents in OpenClaw state directory (default: `~/.openclaw-primary`)
- Delegates to OpenClaw's `openclaw sessions cleanup` for each agent
- Always shows preview before deleting
- Cleans sessions registered in sessions.json according to OpenClaw's maintenance configuration
- Respects OpenClaw's session lifecycle and internal criteria
- Uses same `--state-dir` as watch command for consistency

**What gets cleaned:**
- Registered sessions tracked in sessions.json across all agents (main, claude, etc.)
- Sessions selected by OpenClaw's maintenance settings

**What does NOT get cleaned:**
- Orphaned .jsonl files not tracked in sessions.json (would require custom file scanning - out of scope)

### Configuring Session Maintenance

OpenClaw's cleanup is controlled by maintenance settings in your OpenClaw configuration. **You must configure these settings first** before cleanup will remove any sessions.

#### Recommended Settings

For typical usage, we recommend:
- **Age retention**: 5 days
- **Max entries**: 100 sessions

These settings keep recent history available while preventing unbounded growth.

#### Enable Maintenance

```bash
# Set maintenance mode to "enforce" (required - default is "warn" which only reports)
openclaw config set session.maintenance.mode enforce

# Remove sessions older than 5 days
openclaw config set session.maintenance.pruneAfter 5d

# Cap total sessions at 100 (removes oldest when exceeded)
openclaw config set session.maintenance.maxEntries 100
```

#### Verify Configuration

```bash
openclaw config get session.maintenance
```

Expected output:
```json
{
  "mode": "enforce",
  "pruneAfter": "5d",
  "maxEntries": 100
}
```

#### Test Your Settings

After configuring, test with a dry-run:
```bash
session-monitor cleanup --dry-run
```

You should now see sessions identified for removal.

#### Maintenance Modes

- **`warn`** (default): Only reports what would be cleaned, never deletes
- **`enforce`**: Actually deletes sessions matching criteria

Start with `warn` mode to preview behavior, then switch to `enforce` when ready.

#### Other Settings

```bash
# Different age retention (examples)
openclaw config set session.maintenance.pruneAfter 7d   # Keep 7 days
openclaw config set session.maintenance.pruneAfter 30d  # Keep 30 days
openclaw config set session.maintenance.pruneAfter 12h  # Keep 12 hours

# Different entry limits
openclaw config set session.maintenance.maxEntries 50   # Limit to 50
openclaw config set session.maintenance.maxEntries 200  # Limit to 200
```

**Note:** 
- Maintenance settings are **global** - they apply to all agents (main, claude, rescue, etc.)
- You can also run `openclaw sessions cleanup --enforce --all-agents` directly
- If cleanup reports "0 sessions to prune", check your maintenance configuration

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
