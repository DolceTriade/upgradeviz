#!/usr/bin/env python3
"""
Generate a large test log file with many upgrade events to test scaling
"""

from datetime import datetime, timedelta
import random

def generate_large_test_log(num_gateways=100):
    """Generate a test log with many gateway upgrades"""

    base_time = datetime(2025, 7, 23, 0, 0, 0)
    lines = []

    # Overall upgrade start
    lines.append(f"{base_time.isoformat()}.000000+00:00 Upgrading gateways without controller upgrade...")

    # Generate gateway names
    regions = ['us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1']
    gateway_names = []
    for i in range(num_gateways):
        region = random.choice(regions)
        gateway_names.append(f"gw-{region}-{i:03d}")

    current_time = base_time + timedelta(seconds=5)

    # Generate upgrade starts (mix of explicit and installing status)
    upgrade_starts = {}
    for name in gateway_names:
        if random.random() < 0.7:  # 70% explicit starts
            lines.append(f"{current_time.isoformat()}.{random.randint(100000, 999999)}+00:00 Upgrading {name} to version 8.1.0-1000.{random.randint(1500, 1600)}")
        else:  # 30% installing status starts
            lines.append(f"{current_time.isoformat()}.{random.randint(100000, 999999)}+00:00 Updating upgrade_info to gw {name}: {{'status': 'installing', 'process_status': {{'type': 'Software Upgrade', 'prev_status': 'pending', 'message': 'INSTALLING: Starting upgrade', 'timestamp': None}}}}")

        upgrade_starts[name] = current_time
        current_time += timedelta(seconds=random.randint(1, 3))

    # Generate completions (with some random durations)
    for name in gateway_names:
        if random.random() < 0.9:  # 90% complete successfully
            completion_time = upgrade_starts[name] + timedelta(minutes=random.randint(2, 15))
            curr_ver = f"8.1.0-1000.{random.randint(1580, 1620)}"
            prev_ver = f"8.1.0-1000.{random.randint(1500, 1580)}"
            lines.append(f"{completion_time.isoformat()}.{random.randint(100000, 999999)}+00:00 Updating upgrade_info to gw {name}: {{'status': 'complete', 'curr_ver': '{curr_ver}', 'kernel_ver': '', 'prev_ver': '{prev_ver}', 'process_status': {{'type': 'Software Upgrade', 'update_status': 'complete', 'message': 'Successfully upgraded', 'timestamp': {int(completion_time.timestamp())}}}}}")

    # Sort by timestamp to make realistic log ordering
    lines.sort()
    return lines

if __name__ == '__main__':
    import sys

    num_gateways = 100
    if len(sys.argv) > 1:
        num_gateways = int(sys.argv[1])

    lines = generate_large_test_log(num_gateways)
    for line in lines:
        print(line)
