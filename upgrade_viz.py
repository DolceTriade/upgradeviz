#!/usr/bin/env python3
"""
Gateway Upgrade Visualization Tool

Parses gateway upgrade logs from stdin and generates an interactive SVG Gantt chart
showing the timeline of concurrent gateway upgrades.

Usage: python3 upgrade_viz.py < upgrade_logs.txt > gantt_chart.svg
"""

import sys
import re
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import xml.etree.ElementTree as ET
import math

def debug(msg: str):
    """Print debug messages to stderr"""
    print(f"DEBUG: {msg}", file=sys.stderr)  # Use stderr for debug output


@dataclass
class UpgradeEvent:
    """Represents a gateway upgrade event"""
    gateway_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    version_info: str = ""
    status: str = "in_progress"


def calculate_upgrade_stats(upgrades: List[UpgradeEvent]) -> None:
    """Calculate and debug print statistics about upgrade times"""
    completed_upgrades = [u for u in upgrades if u.end_time is not None]

    if not completed_upgrades:
        debug("No completed upgrades found for statistics")
        return

    # Calculate durations in minutes
    durations = []
    upgrade_durations = []  # Keep track of (gateway_name, duration) pairs

    for upgrade in completed_upgrades:
        duration_seconds = (upgrade.end_time - upgrade.start_time).total_seconds()
        duration_minutes = duration_seconds / 60
        durations.append(duration_minutes)
        upgrade_durations.append((upgrade.gateway_name, duration_minutes))

    # Calculate statistics
    min_duration = min(durations)
    max_duration = max(durations)
    avg_duration = sum(durations) / len(durations)

    # Calculate standard deviation
    variance = sum((d - avg_duration) ** 2 for d in durations) / len(durations)
    std_deviation = math.sqrt(variance)

    # Find gateways with min and max times
    min_gateway = min(upgrade_durations, key=lambda x: x[1])
    max_gateway = max(upgrade_durations, key=lambda x: x[1])

    # Debug print statistics
    debug("=" * 60)
    debug("UPGRADE TIME STATISTICS")
    debug("=" * 60)
    debug(f"Total upgrades: {len(upgrades)}")
    debug(f"Completed upgrades: {len(completed_upgrades)}")
    debug(f"In-progress upgrades: {len(upgrades) - len(completed_upgrades)}")
    debug("")
    debug("Duration Statistics (minutes):")
    debug(f"  Minimum: {min_duration:.2f}m ({min_gateway[0]})")
    debug(f"  Maximum: {max_duration:.2f}m ({max_gateway[0]})")
    debug(f"  Average: {avg_duration:.2f}m")
    debug(f"  Std Dev: {std_deviation:.2f}m")
    debug("")
    debug("Duration Distribution:")

    # Create simple histogram buckets
    buckets = [0, 2, 5, 10, 15, 30, 60, float('inf')]
    bucket_labels = ["<2m", "2-5m", "5-10m", "10-15m", "15-30m", "30-60m", ">60m"]
    bucket_counts = [0] * len(bucket_labels)

    for duration in durations:
        for i, bucket_max in enumerate(buckets[1:]):
            if duration <= bucket_max:
                bucket_counts[i] += 1
                break

    for label, count in zip(bucket_labels, bucket_counts):
        percentage = (count / len(durations)) * 100 if durations else 0
        debug(f"  {label:>6}: {count:3d} upgrades ({percentage:5.1f}%)")

    debug("=" * 60)


class LogParser:
    """Parses gateway upgrade logs and extracts upgrade events"""

    def __init__(self):
        # Regex patterns for different log types
        self.timestamp_pattern = re.compile(r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+\+\d{2}:\d{2})')
        self.upgrade_start_pattern = re.compile(r'Upgrading ([^\s]+) to version(.*)$')
        self.upgrade_complete_pattern = re.compile(
            r"Updating upgrade_info to gw ([^:]+): \{'status': 'complete'.*'curr_ver': '([^']*)'.*\}"
        )
        self.upgrade_installing_pattern = re.compile(
            r"Updating upgrade_info to gw ([^:]+): \{'status': 'installing'.*\}"
        )
        self.overall_start_pattern = re.compile(r'Upgrading gateways without controller upgrade')

        self.upgrades: Dict[str, UpgradeEvent] = {}
        self.overall_start_time: Optional[datetime] = None

    def parse_timestamp(self, line: str) -> Optional[datetime]:
        """Extract timestamp from the beginning of a log line"""
        match = self.timestamp_pattern.match(line)
        if match:
            timestamp_str = match.group(1)
            try:
                return datetime.fromisoformat(timestamp_str.replace('+00:00', '+0000'))
            except ValueError:
                # Try alternative parsing
                return datetime.fromisoformat(timestamp_str)
        return None

    def parse_line(self, line: str) -> None:
        """Parse a single log line and update upgrade events"""
        line = line.strip()
        if not line:
            return

        timestamp = self.parse_timestamp(line)
        if not timestamp:
            return

        # Check for overall upgrade start
        if self.overall_start_pattern.search(line):
            self.overall_start_time = timestamp
            debug("Overall upgrade started at " + str(self.overall_start_time))
            self.upgrades.clear()  # Reset upgrades for new overall upgrade
            return

        # Check for gateway upgrade start
        start_match = self.upgrade_start_pattern.search(line)
        if start_match:
            gateway_name = start_match.group(1)
            version_info = start_match.group(2).strip()

            self.upgrades[gateway_name] = UpgradeEvent(
                gateway_name=gateway_name,
                start_time=timestamp,
                version_info=version_info
            )
            debug(f"Upgrade started for {gateway_name} at {timestamp} with version info: {version_info}")
            return

        # Check for gateway upgrade "installing" status (alternative start indicator)
        installing_match = self.upgrade_installing_pattern.search(line)
        if installing_match:
            gateway_name = installing_match.group(1)

            # Only treat as start if we haven't seen this gateway before
            if gateway_name not in self.upgrades:
                self.upgrades[gateway_name] = UpgradeEvent(
                    gateway_name=gateway_name,
                    start_time=timestamp,
                    version_info="(detected from installing status)"
                )
                debug(f"Upgrade started for {gateway_name} at {timestamp} (detected from installing status)")
            return

        # Check for gateway upgrade completion
        complete_match = self.upgrade_complete_pattern.search(line)
        if complete_match:
            gateway_name = complete_match.group(1)
            curr_version = complete_match.group(2)

            if gateway_name in self.upgrades:
                # Only update if not already complete (avoid duplicate completion updates)
                if self.upgrades[gateway_name].status != "complete":
                    self.upgrades[gateway_name].end_time = timestamp
                    self.upgrades[gateway_name].status = "complete"
                    self.upgrades[gateway_name].version_info += f" -> {curr_version}"
                    debug(f"Upgrade completed for {gateway_name} at {timestamp} with version {curr_version}")
                else:
                    debug(f"Duplicate completion seen for {gateway_name} at {timestamp} - ignoring")
            else:
                # Handle case where we see completion but missed the start
                debug(f"Completion seen for {gateway_name} but no start recorded - creating retroactive entry")
                self.upgrades[gateway_name] = UpgradeEvent(
                    gateway_name=gateway_name,
                    start_time=timestamp,  # Use completion time as start (not ideal but better than nothing)
                    end_time=timestamp,
                    version_info=f"(retroactive) -> {curr_version}",
                    status="complete"
                )

    def parse_logs(self, input_stream) -> List[UpgradeEvent]:
        """Parse all logs from input stream and return list of upgrade events"""
        for line in input_stream:
            self.parse_line(line)

        # Return sorted list of upgrades
        return sorted(self.upgrades.values(), key=lambda x: x.start_time)


class SVGGanttChart:
    """Generates an interactive SVG Gantt chart for gateway upgrades"""

    def __init__(self, width: int = 1200, height: int = 800):
        self.base_width = width
        self.base_height = height
        self.margin = {'top': 60, 'right': 50, 'bottom': 80, 'left': 200}

        # Colors for different states
        self.colors = {
            'complete': '#28a745',      # Green
            'in_progress': '#ffc107',   # Yellow
            'error': '#dc3545'          # Red
        }

    def create_svg_element(self, tag: str, **attrs) -> ET.Element:
        """Helper to create SVG elements with attributes"""
        elem = ET.Element(tag)
        for key, value in attrs.items():
            # Handle special attribute names
            if key == 'class_':
                key = 'class'
            elem.set(key.replace('_', '-'), str(value))
        return elem

    def generate_chart(self, upgrades: List[UpgradeEvent]) -> str:
        """Generate an interactive SVG Gantt chart for the upgrades"""
        if not upgrades:
            return self._create_empty_chart()

        # Calculate dynamic dimensions based on number of upgrades
        min_bar_height = 20  # Minimum readable bar height
        min_spacing = 2      # Minimum spacing between bars
        total_bar_space = len(upgrades) * (min_bar_height + min_spacing)

        # Set dynamic height based on content
        self.height = max(self.base_height, total_bar_space + self.margin['top'] + self.margin['bottom'] + 100)
        self.width = self.base_width
        self.chart_width = self.width - self.margin['left'] - self.margin['right']
        self.chart_height = self.height - self.margin['top'] - self.margin['bottom']

        debug(f"Dynamic chart dimensions: {self.width}x{self.height} for {len(upgrades)} upgrades")

        # Calculate time range
        start_times = [u.start_time for u in upgrades]
        end_times = [u.end_time for u in upgrades if u.end_time]

        if not end_times:
            # If no completions, use current time or add some buffer
            min_time = min(start_times)
            max_time = max(start_times)
            time_span = max_time - min_time
            if time_span.total_seconds() == 0:
                max_time = min_time.replace(second=min_time.second + 60)
        else:
            min_time = min(start_times)
            max_time = max(end_times)

        total_duration = (max_time - min_time).total_seconds()
        if total_duration == 0:
            total_duration = 3600  # 1 hour default

        # Create root SVG element
        svg = self.create_svg_element(
            'svg',
            xmlns="http://www.w3.org/2000/svg",
            viewBox=f"0 0 {self.width} {self.height}",
            width=self.width,
            height=self.height,
            style="background-color: #f8f9fa; font-family: Arial, sans-serif;"
        )

        # Add CSS for interactivity and tooltips
        style = self.create_svg_element('style')
        style.text = """
        .bar { cursor: pointer; stroke: #333; stroke-width: 1; }
        .bar:hover { opacity: 0.8; stroke-width: 2; }
        .gateway-label { font-size: 11px; fill: #333; dominant-baseline: middle; }
        .time-label { font-size: 10px; fill: #666; text-anchor: middle; }
        .title { font-size: 18px; font-weight: bold; fill: #333; text-anchor: middle; }
        .chart-area { cursor: grab; }
        .chart-area:active { cursor: grabbing; }

        /* SVG Tooltip styles */
        .svg-tooltip {
            fill: rgba(0, 0, 0, 0.9);
            stroke: rgba(255, 255, 255, 0.2);
            stroke-width: 1;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.2s ease-in-out;
        }

        .tooltip-text {
            fill: white;
            font-size: 12px;
            font-family: Arial, sans-serif;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.2s ease-in-out;
        }

        .bar:hover + .svg-tooltip,
        .bar:hover + .svg-tooltip + .tooltip-text {
            opacity: 1;
        }
        """
        svg.append(style)

        # Add title
        title = self.create_svg_element(
            'text',
            x=self.width // 2,
            y=30,
            class_='title'
        )
        title.text = "Gateway Upgrade Timeline"
        svg.append(title)

        # Create chart group
        chart_group = self.create_svg_element(
            'g',
            transform=f"translate({self.margin['left']}, {self.margin['top']})",
            class_='chart-area'
        )
        svg.append(chart_group)

        # Draw time axis
        self._draw_time_axis(chart_group, min_time, max_time, total_duration)

        # Draw gateway bars
        bar_height = max(min_bar_height, min(25, self.chart_height // len(upgrades) - 2))
        y_step = max(bar_height + min_spacing, self.chart_height / len(upgrades))

        debug(f"Bar dimensions: height={bar_height}, step={y_step}")

        for i, upgrade in enumerate(upgrades):
            y_pos = i * y_step + (y_step - bar_height) / 2

            # Calculate bar position and width
            start_offset = (upgrade.start_time - min_time).total_seconds()
            x_pos = (start_offset / total_duration) * self.chart_width

            if upgrade.end_time:
                duration = (upgrade.end_time - upgrade.start_time).total_seconds()
                bar_width = max(2, (duration / total_duration) * self.chart_width)
                color = self.colors['complete']
            else:
                # Show incomplete upgrades as extending to the end
                bar_width = self.chart_width - x_pos
                color = self.colors['in_progress']

            # Draw gateway label with smart truncation for very long names
            gateway_display_name = upgrade.gateway_name
            if len(gateway_display_name) > 25:  # Truncate very long names
                gateway_display_name = gateway_display_name[:22] + "..."

            label = self.create_svg_element(
                'text',
                x=-10,
                y=y_pos + bar_height / 2,
                class_='gateway-label',
                text_anchor='end'
            )
            label.text = gateway_display_name
            chart_group.append(label)

            # Draw upgrade bar
            bar = self.create_svg_element(
                'rect',
                x=x_pos,
                y=y_pos,
                width=bar_width,
                height=bar_height,
                fill=color,
                class_='bar'
            )
            chart_group.append(bar)

            # Add SVG native tooltip using <title> element
            tooltip_text = f"Gateway: {upgrade.gateway_name}\nStart: {upgrade.start_time.strftime('%H:%M:%S')}"
            if upgrade.end_time:
                duration_seconds = (upgrade.end_time - upgrade.start_time).total_seconds()
                duration_mins = duration_seconds / 60
                duration_hours = duration_mins / 60

                # Format duration nicely
                if duration_seconds < 60:
                    duration_str = f"{duration_seconds:.1f}s"
                elif duration_mins < 60:
                    duration_str = f"{duration_mins:.1f}m"
                else:
                    duration_str = f"{duration_hours:.1f}h"

                tooltip_text += f"\nEnd: {upgrade.end_time.strftime('%H:%M:%S')}\nDuration: {duration_str}"
                tooltip_text += f"\n({duration_mins:.2f} minutes)"
            else:
                tooltip_text += "\nStatus: In Progress"

            if upgrade.version_info:
                tooltip_text += f"\nVersion: {upgrade.version_info}"

            # Create title element for native SVG tooltip
            title = self.create_svg_element('title')
            title.text = tooltip_text
            bar.append(title)

        # Add JavaScript for zoom and pan functionality
        script = self.create_svg_element('script')
        script.text = """
        <![CDATA[
        let scale = 1;
        let panX = 0;
        let panY = 0;
        let isPanning = false;
        let startPanX = 0;
        let startPanY = 0;

        const chartArea = document.querySelector('.chart-area');

        // Zoom functionality
        document.addEventListener('wheel', function(e) {
            if (e.target.closest('svg')) {
                e.preventDefault();
                const delta = e.deltaY > 0 ? 0.9 : 1.1;
                scale *= delta;
                scale = Math.max(0.1, Math.min(5, scale));
                updateTransform();
            }
        });

        // Pan functionality
        chartArea.addEventListener('mousedown', function(e) {
            isPanning = true;
            startPanX = e.clientX - panX;
            startPanY = e.clientY - panY;
        });

        document.addEventListener('mousemove', function(e) {
            if (isPanning) {
                panX = e.clientX - startPanX;
                panY = e.clientY - startPanY;
                updateTransform();
            }
        });

        document.addEventListener('mouseup', function() {
            isPanning = false;
        });

        function updateTransform() {
            chartArea.style.transform = `translate(${panX}px, ${panY}px) scale(${scale})`;
        }
        ]]>
        """
        svg.append(script)

        return self._element_to_string(svg)

    def _draw_time_axis(self, parent: ET.Element, min_time: datetime, max_time: datetime, total_duration: float):
        """Draw time axis with labels"""
        # Axis line
        axis_line = self.create_svg_element(
            'line',
            x1=0,
            y1=self.chart_height + 10,
            x2=self.chart_width,
            y2=self.chart_height + 10,
            stroke='#333',
            stroke_width=1
        )
        parent.append(axis_line)

        # Time labels
        num_ticks = 8
        for i in range(num_ticks + 1):
            x_pos = (i / num_ticks) * self.chart_width
            time_offset = (i / num_ticks) * total_duration
            tick_time = min_time.replace(microsecond=0) + \
                       timedelta(seconds=time_offset)

            # Tick mark
            tick = self.create_svg_element(
                'line',
                x1=x_pos,
                y1=self.chart_height + 10,
                x2=x_pos,
                y2=self.chart_height + 15,
                stroke='#333',
                stroke_width=1
            )
            parent.append(tick)

            # Tick label
            label = self.create_svg_element(
                'text',
                x=x_pos,
                y=self.chart_height + 30,
                class_='time-label'
            )
            label.text = tick_time.strftime('%H:%M:%S')
            parent.append(label)

    def _create_empty_chart(self) -> str:
        """Create an empty chart when no data is available"""
        svg = self.create_svg_element(
            'svg',
            xmlns="http://www.w3.org/2000/svg",
            viewBox=f"0 0 {self.base_width} {self.base_height}",
            width=self.base_width,
            height=self.base_height,
            style="background-color: #f8f9fa; font-family: Arial, sans-serif;"
        )

        text = self.create_svg_element(
            'text',
            x=self.base_width // 2,
            y=self.base_height // 2,
            text_anchor='middle',
            style='font-size: 18px; fill: #666;'
        )
        text.text = "No upgrade data found in logs"
        svg.append(text)

        return self._element_to_string(svg)

    def _element_to_string(self, element: ET.Element) -> str:
        """Convert XML element to string with proper formatting"""
        return ET.tostring(element, encoding='unicode', method='xml')


def main():
    """Main function to parse logs and generate SVG chart"""
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print(__doc__)
        sys.exit(0)

    # Parse logs from stdin
    parser = LogParser()
    upgrades = parser.parse_logs(sys.stdin)

    if not upgrades:
        print("No gateway upgrades found in the provided logs.", file=sys.stderr)
        sys.exit(1)

    debug(f"Parsed {len(upgrades)} upgrade events")

    # Calculate and print statistics
    calculate_upgrade_stats(upgrades)

    # Generate SVG chart
    chart_generator = SVGGanttChart()
    svg_content = chart_generator.generate_chart(upgrades)

    # Output SVG to stdout
    print(svg_content)


if __name__ == '__main__':
    main()
