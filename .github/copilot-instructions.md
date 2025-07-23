# Copilot Instructions

<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

This is a Python project for parsing gateway upgrade logs and generating interactive SVG Gantt chart visualizations.

## Project Context
- Parse logs from stdin with timestamps in ISO format (2025-07-23T00:00:02.976005+00:00)
- Track gateway upgrade start/end times from log patterns
- Generate zoomable and scrollable SVG Gantt charts
- Handle concurrent upgrades with no fixed batch sizes

## Key Log Patterns
- "Upgrading gateways without controller upgrade..." - marks overall upgrade start
- "Upgrading {gateway_name} to version" - marks individual gateway upgrade start
- "Updating upgrade_info to gw {gateway_name}: {'status': 'installing'..." - alternative upgrade start (handles log rate limiting)
- "Updating upgrade_info to gw {gateway_name}: {'status': 'complete'..." - marks gateway upgrade completion

## Robust Handling
- Detects upgrade starts from "installing" status when explicit starts are missing due to log rate limiting
- Prevents duplicate completion updates for already-completed upgrades
- Creates retroactive entries for orphaned completion messages
- Gracefully handles malformed or missing log entries

## Dependencies
- Standard library only preferred (datetime, sys, xml.etree, etc.)
- Focus on clean, readable code for log parsing and SVG generation
