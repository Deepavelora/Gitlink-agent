# GitLink — Opportunity Hunter Agent

![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)
![tag:hackathon](https://img.shields.io/badge/hackathon-5F43F1)

## Overview

GitLink is an AI-powered opportunity discovery agent that helps students find relevant internships, entry-level jobs, and other career opportunities from multiple sources.

Instead of manually checking multiple websites, users can search by skills and interests and receive matching listings with source links and relevant keywords.

## Problem Statement

Students often miss suitable opportunities because listings are scattered across different platforms. Searching manually takes time and makes it difficult to identify relevant opportunities.

## Solution

GitLink searches supported opportunity sources, matches listings against user-provided keywords, removes duplicate links, and returns results with their source and original listing URL.

## Features

- Search opportunities using keywords such as Python, data analytics, and engineering.
- Retrieve listings from supported public job APIs.
- Rank results by the number of matched keywords.
- Remove duplicate listings.
- Display company, location, source, matching keywords, and original URL.
- Provide a conversational agent interface using the uAgents Chat Protocol.

## Technology Stack

- Python
- Fetch.ai uAgents
- Agent Chat Protocol (ACP)
- Requests
- Arbeitnow Job Board API
- Remotive API

## Project Structure

```text
Gitlink-agent/
├── main.py
├── opportunity_search.py
├── github_search.py
├── requirements.txt
└── README.md
```

## Setup and Run

### 1. Clone the repository

```bash
git clone https://github.com/Deepavelora/Gitlink-agent.git
cd Gitlink-agent
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

### 3. Install dependencies

On Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 4. Search opportunities directly

```powershell
.\.venv\Scripts\python.exe opportunity_search.py
```

Enter keywords when prompted, for example:

```text
python internship
```

### 5. Run the conversational agent

```powershell
.\.venv\Scripts\python.exe main.py
```

Follow the Fetch.ai Agentverse instructions to configure the agent mailbox and make it available for supported chat integrations.

## Limitations

- Results depend on the availability and quality of supported public APIs.
- Keyword matching may return listings that are not a perfect fit.
- Always verify eligibility, application deadlines, and requirements on the original listing.
- This version does not guarantee that every listing is an internship or that every opportunity is still open.

## Hackathon

**Event:** Fetch-a-Thon 3.0

**Category:** Innovation Lab

**Goal:** Make opportunity discovery easier by bringing listings from multiple sources into one conversational experience.

## Agent Details

- **Agent name:** `gitlink_opportunity_agent`
- **Agent address:** Add the registered agent address after completing Agentverse setup.
- **ASI:One chat URL:** Add after the agent is connected and tested.

## Future Improvements

- Better internship and entry-level job filtering.
- Eligibility and deadline extraction.
- Personalized matching based on student skills and location.
- Additional opportunity sources and improved ranking.

