#!/usr/bin/env python3
"""
Test script for the upgrade visualization tool
"""

import subprocess
import sys
import os

def run_test():
    """Run a test with sample logs and open the result"""

    # Get the script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    python_exe = os.path.join(script_dir, '.venv', 'bin', 'python')
    upgrade_script = os.path.join(script_dir, 'upgrade_viz.py')
    sample_logs = os.path.join(script_dir, 'sample_logs.txt')
    output_svg = os.path.join(script_dir, 'test_output.svg')

    print("Running upgrade visualization test...")

    try:
        # Run the visualization tool
        with open(sample_logs, 'r') as input_file:
            with open(output_svg, 'w') as output_file:
                result = subprocess.run(
                    [python_exe, upgrade_script],
                    stdin=input_file,
                    stdout=output_file,
                    stderr=subprocess.PIPE,
                    text=True
                )

        if result.returncode == 0:
            print(f"✅ Successfully generated SVG: {output_svg}")
            print(f"📊 Open the file in a web browser to view the interactive Gantt chart")

            # Show file size
            file_size = os.path.getsize(output_svg)
            print(f"📁 File size: {file_size} bytes")

        else:
            print(f"❌ Error occurred:")
            print(result.stderr)
            return False

    except Exception as e:
        print(f"❌ Exception occurred: {e}")
        return False

    return True

if __name__ == '__main__':
    success = run_test()
    sys.exit(0 if success else 1)
