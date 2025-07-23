# Gateway Upgrade Visualization Tool

A Python tool for parsing gateway upgrade logs and generating interactive SVG Gantt charts to visualize upgrade timelines and concurrency.

## Features

- **Log Parsing**: Parses gateway upgrade logs from stdin with ISO timestamp format
- **Timeline Visualization**: Generates interactive SVG Gantt charts showing upgrade duration and concurrency
- **Interactive SVG**: Zoomable and scrollable charts with hover tooltips
- **Concurrent Upgrades**: Visualizes multiple simultaneous gateway upgrades
- **No Dependencies**: Uses only Python standard library

## Usage

### Basic Usage
```bash
python upgrade_viz.py < upgrade_logs.txt > gantt_chart.svg
```

### Piping from log files
```bash
cat /path/to/upgrade.log | python upgrade_viz.py > timeline.svg
```

### Real-time monitoring
```bash
tail -f /path/to/upgrade.log | python upgrade_viz.py > live_chart.svg
```

## Log Format

The tool recognizes these log patterns:

1. **Overall upgrade start**:
   ```
   2025-07-23T00:00:02.976005+00:00 Upgrading gateways without controller upgrade...
   ```

2. **Gateway upgrade start** (explicit):
   ```
   2025-07-23T00:00:05.123456+00:00 Upgrading alta2-aep-edge-1 to version 8.1.0-1000.1568
   ```

3. **Gateway upgrade start** (from installing status - handles log rate limiting):
   ```
   2025-07-23T00:00:09.345678+00:00 Updating upgrade_info to gw alta2-aws-use2-s16-hagw: {'status': 'installing', 'process_status': {'type': 'Software Upgrade', 'prev_status': 'failed', 'message': 'INSTALLING: No recent event message', 'timestamp': None}}
   ```

4. **Gateway upgrade completion**:
   ```
   2025-07-23T00:05:30.987654+00:00 Updating upgrade_info to gw alta2-aep-edge-1: {'status': 'complete', 'curr_ver': '8.1.0-1000.1568', 'kernel_ver': '', 'prev_ver': '8.1.0-1000.1556', 'process_status': {'type': 'Software Upgrade', 'update_status': 'complete', 'message': 'Successfully upgraded', 'timestamp': 1753223782}}
   ```

## Robust Log Handling

- **Log Rate Limiting**: Detects upgrade starts from "installing" status messages when explicit start messages are dropped
- **Duplicate Prevention**: Ignores duplicate completion messages for already-completed upgrades
- **Missing Starts**: Creates retroactive entries for completions without corresponding starts
- **Malformed Lines**: Gracefully skips invalid log entries

## Output

The tool generates an interactive SVG file with:

- **Gantt Chart**: Horizontal bars showing upgrade duration for each gateway
- **Color Coding**:
  - Green: Completed upgrades
  - Yellow: In-progress upgrades
- **Interactive Features**:
  - Mouse wheel zoom in/out
  - Click and drag to pan
  - Hover tooltips showing:
    - Gateway name (full name even if truncated)
    - Start and end times
    - Duration in seconds/minutes/hours
    - Precise duration in minutes
    - Version information
    - Status (complete/in-progress)
- **Timeline**: X-axis shows time progression with labeled ticks
- **Gateway Names**: Y-axis shows gateway identifiers

## Examples

### Sample Log Input
```
2025-07-23T00:00:02.976005+00:00 Upgrading gateways without controller upgrade...
2025-07-23T00:00:05.123456+00:00 Upgrading alta2-aep-edge-1 to version 8.1.0-1000.1568
2025-07-23T00:00:07.234567+00:00 Upgrading alta2-aep-edge-2 to version 8.1.0-1000.1568
2025-07-23T00:05:30.987654+00:00 Updating upgrade_info to gw alta2-aep-edge-1: {'status': 'complete', 'curr_ver': '8.1.0-1000.1568', ...}
2025-07-23T00:06:15.456789+00:00 Updating upgrade_info to gw alta2-aep-edge-2: {'status': 'complete', 'curr_ver': '8.1.0-1000.1568', ...}
```

### Generated Visualization
The output SVG will show:
- Two horizontal bars representing the two gateway upgrades
- Start times aligned with the log timestamps
- Duration bars showing the time from start to completion
- Interactive tooltips with detailed upgrade information

## Technical Details

- **Language**: Python 3.6+
- **Dependencies**: None (standard library only)
- **Input**: Reads from stdin
- **Output**: SVG format to stdout
- **Timestamp Format**: ISO 8601 with timezone (e.g., `2025-07-23T00:00:02.976005+00:00`)

## File Structure

```
upgradeviz/
├── upgrade_viz.py          # Main visualization script
├── requirements.txt        # Dependencies (none required)
├── README.md              # This file
└── .github/
    └── copilot-instructions.md  # Development guidelines
```

## Error Handling

- Invalid timestamp formats are skipped with warnings
- Missing completion events show upgrades as "in-progress"
- Empty input generates an informative empty chart
- Malformed log lines are ignored gracefully

## Development

The project is now fully set up and ready to use! Here's what's included:

### Files Created
- `upgrade_viz.py` - Main visualization script
- `test_viz.py` - Test script with sample data
- `sample_logs.txt` - Example log file for testing
- `requirements.txt` - Dependencies (none required)
- `.vscode/tasks.json` - VS Code tasks for easy development

### VS Code Tasks Available
- **Test Upgrade Visualization** - Run the test script
- **Generate SVG from Sample Logs** - Create SVG from sample data
- **Open Generated SVG** - View the generated chart

### Quick Start
1. Run the test: `python test_viz.py`
2. View the generated `test_output.svg` in your browser
3. Modify `sample_logs.txt` or use your own log files

The tool consists of three main classes:

1. **LogParser**: Handles log parsing and event extraction
2. **UpgradeEvent**: Data structure for upgrade information
3. **SVGGanttChart**: Generates interactive SVG visualizations

To extend functionality, modify the regex patterns in `LogParser` or add new visualization features to `SVGGanttChart`.
