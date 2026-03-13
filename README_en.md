# Slack Mention Analysis Dashboard

**[日本語](README.md)** | **English**

A tool that visualizes mention relationships within Slack channels as a network graph.
It analyzes communication structures from three types of interactions — @mentions, thread replies, and reactions — to detect communities and identify key persons.

**[View Demo (Sample Data)](https://9BwgeBTPG-QH.github.io/slack-mention-map/)** — Explore the dashboard with fictional team data.

## Features

- `/mention-map [days]` slash command to trigger analysis (default 30 days, max 730 days)
- Real-time progress notifications via DM thread; browser opens automatically on completion
- Exclusive lock to prevent concurrent execution (one channel at a time)

### Dashboard

- **Network View**: Physics-simulated network graph powered by vis.js
  - Click a node to drill down into its connections (with breadcrumb navigation)
  - Double-click to collapse/expand community clusters
  - Automatic community boundary drawing with Convex Hull
  - Node size proportional to activity (sent + received + reaction count)
- **Word Cloud View**: Name word cloud scaled by mention frequency
  - Click a name to jump to the corresponding node in Network view
- **Side Panel**: Detailed statistics shown when a node is selected
  - Sent / Received / Reaction counts
  - Breakdown of mention targets, reaction targets, and sources (clickable for navigation)
  - Hub / Passive Observer badge display
- **Legend Panel**: Community list (with member name preview) and Passive Observer list
  - Click to zoom to community members
- **Export**: PNG image / Standalone HTML

### Analysis

- **Community Detection**: Automatic grouping via the Louvain method
- **Hub Detection**: Top 20 identified by Degree centrality + Betweenness centrality score
- **Passive Observer Detection**: Identifies users who participate only through reactions without sending messages (CC ratio above threshold)

## Architecture

```
Slack API (messages + threads + reactions)
    │
    ▼
build_dataframe()        ← Convert Slack messages to DataFrame
    │                       (mentions→to, thread participants→to, reactions→cc)
    ▼
run_analysis_pipeline()  ← NetworkX: Build graph → Louvain → Centrality
    │
    ▼
/vis-data (JSON)         ← Served via local HTTP server
    │
    ▼
template.html            ← Rendered with vis.js + wordcloud2.js
```

### Data Transformation Mapping

Slack message data is converted into an email-like DataFrame structure for network analysis.

| Slack Concept | Analysis Concept | Mapping |
|---------------|-----------------|---------|
| Message author | from (sender) | `user_id` → `from_email` |
| @mention target | to (recipient) | `<@USER_ID>` parsed via regex |
| Thread participants | to (recipient) | All other posters in the thread (including parent message) |
| Reactions | cc (passive participation) | Users who reacted (excluding those already in `to`) |
| First 50 chars of message | subject | Message preview |

## Requirements

- Python 3.10+
- Slack Bot Token (`SLACK_BOT_TOKEN`)
- Slack App Token (`SLACK_APP_TOKEN`) — for Socket Mode

## Installation

```bash
git clone https://github.com/9BwgeBTPG-QH/slack-mention-map.git
cd slack-mention-map
pip install -r requirements.txt
```

## Slack App Setup

### Option 1: Using App Manifest (Recommended)

1. Go to [Slack API](https://api.slack.com/apps) and click "Create New App"
2. Select "From an app manifest"
3. Choose your workspace
4. Paste the contents of `manifest.json` from this repository and click "Create"

### Option 2: Manual Configuration

<details>
<summary>Show manual setup steps</summary>

1. Go to [Slack API](https://api.slack.com/apps), select "Create New App" → "From scratch"
2. Enter an app name (e.g., "mention-map"), choose your workspace, and click "Create App"

**Bot Token Scopes** (under "OAuth & Permissions"):
- `channels:history` — Read channel message history
- `channels:read` — Read channel information
- `chat:write` — Send messages
- `im:write` — Send direct messages
- `users:read` — Read user information
- `commands` — Use slash commands

**Slash Commands**:
- Command: `/mention-map`
- Short Description: Visualize mention relationships in the channel
- Usage Hint: [days] (optional)

**Socket Mode**: Enable under the "Socket Mode" section
</details>

### Obtaining Tokens

1. Go to "Socket Mode" → Enable Socket Mode
2. Under "Basic Information" → "App-Level Tokens", generate a new token
   - Enter a token name (e.g., `socket-token`)
   - Select the required scope (`connections:write`)
3. Copy the generated App Token (starts with `xapp-`)
4. Go to "Install App" → "Install to Workspace"
5. Copy the Bot User OAuth Token (starts with `xoxb-`)

### Setting Environment Variables

```bash
cp .env.example .env
```

Edit `.env` with your actual tokens:

```env
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token
```

See comments in `.env.example` for analysis parameter customization.

## Usage

### Starting the App

```bash
python slack-mention-map.py
```

A local HTTP server starts on port 8000 (tries ports 8001–8009 sequentially if 8000 is in use).

### Running an Analysis

1. Invite the bot to the channel you want to analyze:
   ```
   /invite @mention-map
   ```

2. Run the slash command:
   ```
   /mention-map        # Default: past 30 days
   /mention-map 90     # Past 90 days
   /mention-map 365    # Past year (max 730 days)
   ```

3. Progress is reported in real-time via DM thread:
   - Message fetch → Thread reply fetch → DataFrame conversion → Network analysis
   - On completion, the browser opens automatically to display the dashboard

### Dashboard Controls

| Action | Behavior |
|--------|----------|
| Click a node | Drill down to connections + show details in side panel |
| Click empty space | Reset to full view |
| Double-click a node | Collapse/expand the community into a single cluster node |
| Click a community in legend | Zoom to that community's members |
| Click a Passive Observer in legend | Focus on that node |
| Network / Word Cloud button | Toggle between views |
| Click a name in Word Cloud | Switch to Network view and jump to that node |
| PNG button | Download the network graph as an image |
| HTML button | Export the entire dashboard as a standalone HTML file |

## Export

### PNG

The "PNG" button in the toolbar saves the current network graph as an image in its current canvas state.

Filename: `slack_network_{channel_name}_{days}days_{date}.png`

### HTML

The "HTML" button in the toolbar downloads the analysis results as a standalone HTML file.

- **For sharing & archiving**: Analysis JSON is embedded in the file, so no server is needed
- **Full functionality**: Node click, community collapse, Convex Hull, Word Cloud toggle — everything works
- **Dark theme**: Retains the same Dark Obsidian theme as the live view
- vis.js / wordcloud2.js are loaded from CDN, so internet access is required when viewing

Filename: `slack_network_{channel_name}_{days}days_{date}.html`

## Analysis Parameters

The following parameters can be adjusted in `.env` (all optional).

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `MENTION_MAP_CC_THRESHOLD` | `0.30` | Passive Observer detection threshold. Detected when CC count / total messages ≥ this value |
| `MENTION_MAP_MIN_EDGE_WEIGHT` | `1` | Minimum edge weight for display. Increase to reduce noise |
| `MENTION_MAP_HUB_DEGREE_W` | `0.5` | Weight of Degree centrality in hub score |
| `MENTION_MAP_HUB_BETWEEN_W` | `0.5` | Weight of Betweenness centrality in hub score |
| `MENTION_MAP_COMPANY_DOMAINS` | (none) | Internal domain list (comma-separated). If unset, all users are treated as internal |

## File Structure

```
slack-mention-map/
├── slack-mention-map.py   Slack Bot (Socket Mode) + HTTP server + data conversion
├── core.py                Analysis pipeline (NetworkX + Louvain + Centrality)
├── template.html          Dashboard UI (vis.js + wordcloud2.js)
├── manifest.json          Slack App Manifest (for setup)
├── requirements.txt       Python package list
├── .env.example           Environment variable template
└── .env                   Slack tokens + analysis parameters (create manually, not tracked by git)
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Slack Integration | slack-bolt, slack-sdk (Socket Mode) |
| Data Transformation | pandas (DataFrame) |
| Network Analysis | NetworkX (directed graph, Louvain community detection, Degree/Betweenness centrality) |
| Frontend | vis.js (network graph + Barnes-Hut physics simulation), wordcloud2.js |
| Visualization Helpers | Canvas API (Convex Hull rendering, Graham Scan algorithm) |
| HTTP Server | Python http.server (local serving only) |

## Troubleshooting

| Symptom | Solution |
|---------|----------|
| `not_allowed_token_type` error | Verify the App Token starts with `xapp-` |
| Token not set error | Check that `SLACK_BOT_TOKEN` and `SLACK_APP_TOKEN` are set in `.env` |
| Browser doesn't open | Manually enter the `http://localhost:8000` URL shown in the DM |
| Message fetch error | Verify the bot has `channels:history` permission and is invited to the channel |
| "Another analysis is running" | Wait for the previous analysis to finish (exclusive lock prevents concurrent execution) |
| Rate limit error | Handled with automatic retry (up to 3 times, respects `Retry-After` header). May take time for large message volumes |
| Port 8000 in use | Ports 8001–8009 are tried automatically |
| Too much noise in results | Increase `MENTION_MAP_MIN_EDGE_WEIGHT` to filter out weak edges |

## Notes

- The HTTP server only serves `/` and `/vis-data`; all other paths return 404 (prevents `.env` file leaks, etc.)
- The dashboard is accessible only while the application is running (use HTML export to save results)
- For large graphs with 200+ nodes, Betweenness centrality is approximated with k=100 sampling
- Keep tokens secure and never publish the `.env` file to GitHub or other public repositories

## License

MIT
