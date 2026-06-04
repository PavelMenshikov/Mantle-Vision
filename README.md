![Mantle Vision Banner](logo.png)

# Mantle Vision

**Autonomous AI Trading Agent for Mantle Network**

[![Built for Mantle](https://img.shields.io/badge/Built%20for-Mantle-FFD700?style=for-the-badge&logo=ethereum&logoColor=FFD700)](https://mantle.xyz)
[![Hackathon](https://img.shields.io/badge/Turing%20Test-2026-8A2BE2?style=for-the-badge)](https://dorahacks.io/hackathon/mantle-turing-test)
[![Phase II](https://img.shields.io/badge/Phase-AI%20Awakening-00FF88?style=for-the-badge)](https://dorahacks.io/hackathon/mantle-turing-test)

[![Vue 3](https://img.shields.io/badge/Vue-3-4FC08D?style=flat-square&logo=vue.js)](https://vuejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Solidity](https://img.shields.io/badge/Solidity-0.8-363636?style=flat-square&logo=solidity)](https://soliditylang.org/)
[![Tailwind](https://img.shields.io/badge/Tailwind-3-06B6D4?style=flat-square&logo=tailwindcss)](https://tailwindcss.com/)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-412991?style=flat-square&logo=openai)](https://openai.com/)
[![AltLLM](https://img.shields.io/badge/AltLLM-Crypto%20AI-FF6B6B?style=flat-square)](https://altllm.ai/)
[![License](https://img.shields.io/badge/License-MIT-22A7F0?style=flat-square)](LICENSE)

---

<p align="center">
  <b>Real-time on-chain intelligence • AI-powered trading signals • Autonomous paper trading • Telegram alerts</b>
</p>

<p align="center">
  <i>An entry for the Mantle Turing Test Hackathon 2026 — Phase II: AI Awakening</i>
</p>

---

## Overview

Mantle Vision is an autonomous AI agent that monitors the Mantle blockchain in real time, analyzes whale movements and DeFi activity, generates trading signals, and executes paper trades — all without human intervention. It features a cyberpunk-styled dashboard and a Telegram bot for mobile notifications.

### Tracks & Prizes
| Track | Prize | Target |
|-------|-------|--------|
| **AI Alpha & Data** | $8,500 | On-chain AI analysis |
| **AI Trading & Strategy** | $3,500 | Autonomous trading agent |
| **Best AI Agent** | $200 | Agent usability & innovation |
| **Best UI/UX** | $3,000 | Dashboard experience |

---

## Screenshots

### Dashboard
Real-time portfolio value, P&L, active signals, and network status — all in one place.
![Dashboard](dashboard.png)

### Signals
AI-generated trading signals with direction, confidence score, and reasoning from each analysis cycle.
![Signals](signals.png)

### Whales
On-chain whale tracking — live blockscan for large transfers and protocol interactions on Mantle.
![Whales](whales.png)

---

## Features

### 🤖 Autonomous Trading Agent
- Scans Mantle blocks every 120s for whale transfers & protocol interactions
- AI analysis with 3-provider fallback chain: **OpenAI → Groq → AltLLM**
- Autonomous BUY/SELL/HOLD decisions based on real on-chain data
- Paper trading engine with $10K virtual capital, live P&L tracking
- **10 AI API calls per cycle** (3 assets × 3 analyses + 1 summary)

### 📊 Live Dashboard
- Real-time signal feed with confidence indicators
- Portfolio positions & performance chart
- Whale activity monitor
- Token price ticker (CoinGecko)

### 📱 Telegram Notifier
- Trade execution alerts
- Whale movement warnings
- AI signal notifications
- Agent status reports

### ⛓️ On-Chain Identity (ERC-8004)
- Agent registration on Mantle via ERC-8004 contract
- Verified on-chain signal recording
- Accuracy tracking

---

## Architecture

```
mantle-vision/
├── frontend/                      # Vue 3 + Vite + Tailwind
│   ├── src/
│   │   ├── components/           # GlassCard, NeonButton, SignalCard, WalletConnect...
│   │   ├── views/                # Dashboard, Signals, Portfolio, Whales, Settings
│   │   ├── stores/               # Pinia: wallet, signals, portfolio
│   │   └── composables/          # WebSocket real-time client
│   └── vite.config.js            # Proxy to backend :8000
│
├── backend/                       # FastAPI + AI + Blockchain
│   ├── app/
│   │   ├── api/                  # REST: /signals, /whales, /portfolio, /auth, /ws
│   │   ├── services/
│   │   │   ├── mantle_scanner.py # Real Mantle block scanner
│   │   │   ├── nansen.py         # Whale tracking (real data fallback)
│   │   │   ├── analyzer.py       # AI analysis (OpenAI → Groq → AltLLM)
│   │   │   ├── trading_agent.py  # Autonomous decision engine
│   │   │   ├── dex_trader.py     # On-chain DEX swap execution
│   │   │   ├── paper_trading.py  # Virtual portfolio engine
│   │   │   ├── price_feed.py     # Live CoinGecko prices
│   │   │   └── telegram_bot.py   # Telegram notification service
│   │   ├── blockchain/           # Mantle RPC client & contract interactions
│   │   └── models/               # Pydantic schemas
│   └── requirements.txt
│
├── contracts/                     # Solidity
│   ├── AgentIdentity.sol         # ERC-8004 agent identity
│   └── SignalRecorder.sol        # On-chain signal ledger
│
├── .env.example                   # Environment template
└── README.md
```

---

## Quick Start

### Prerequisites
```bash
# Backend
cd mantle-vision/backend
pip install -r requirements.txt

# Frontend
cd mantle-vision/frontend
npm install
```

### Configure Environment
```bash
cp .env.example .env
# Edit .env with your API keys (see .env.example for required fields)
```

### Run
```bash
# Terminal 1 — Backend (FastAPI)
cd mantle-vision/backend
uvicorn app.main:app --reload --port 8000
# → http://localhost:8000/docs

# Terminal 2 — Frontend (Vue 3)
cd mantle-vision/frontend
npm run dev
# → http://localhost:3000
```

### Verify
```bash
curl http://localhost:8000/health
# → {"status":"ok","blockchain":"mantle","block":39541546,"mode":"demo"}
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Server status & current block |
| GET | `/api/signals` | List signals (paginated, filterable) |
| GET | `/api/signals/{id}` | Signal details |
| POST | `/api/signals/generate` | Generate AI signal |
| GET | `/api/whales` | List tracked whales |
| POST | `/api/whales` | Add whale address |
| DELETE | `/api/whales/{address}` | Remove whale |
| GET | `/api/whales/{address}/activity` | Whale activity feed |
| GET | `/api/portfolio` | Portfolio positions |
| GET | `/api/portfolio/pnl` | P&L history chart data |
| GET | `/api/portfolio/history` | Trade history |
| POST | `/api/portfolio/trade` | Execute paper trade |
| GET | `/api/auth/nonce/{address}` | Get SIWE nonce |
| POST | `/api/auth/verify` | Verify wallet signature |
| GET | `/api/auth/session` | Check session validity |
| WS | `/ws` | Real-time signal stream |

---

## AI Provider Fallback Chain

```
┌─────────┐    ┌────────┐    ┌──────────┐    ┌───────────┐
│ OpenAI  │ →  │  Groq  │ →  │  AltLLM  │ →  │ Fallback  │
│ GPT-4o  │    │Mixtral │    │crypto-ai │    │determin.  │
└─────────┘    └────────┘    └──────────┘    └───────────┘
```

| Provider | Key Status | Model | Cost | Specialty |
|----------|-----------|-------|------|-----------|
| OpenAI | ✅ | `gpt-4o-mini` | ~$0.15/1M tokens | JSON mode, structured output |
| Groq | ✅ | `mixtral-8x7b-32768` | Free | Fast inference |
| AltLLM | ✅ | `altllm-basic` | $5/1M tokens | Built-in CoinGecko, crypto news, gas data |

---

## Smart Contract Addresses

| Contract | Address | Network |
|----------|---------|---------|
| AgentIdentity (ERC-8004) | *TBD — deploy after Phase II* | Mantle Sepolia |
| SignalRecorder | *TBD — deploy after Phase II* | Mantle Sepolia |

---

## Tech Stack

![Vue.js](https://img.shields.io/badge/Vue_3-4FC08D?style=for-the-badge&logo=vue.js&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Web3](https://img.shields.io/badge/Web3.py-F16822?style=for-the-badge&logo=web3.js&logoColor=white)
![Solidity](https://img.shields.io/badge/Solidity-363636?style=for-the-badge&logo=solidity&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)

**Frontend:** Vue 3, Vite, Tailwind CSS, Pinia, Chart.js, Ethers.js  
**Backend:** FastAPI, Uvicorn, Web3.py, OpenAI SDK, httpx, aiogram  
**Contracts:** Solidity 0.8.20, OpenZeppelin, ERC-721 (ERC-8004)  
**Blockchain:** Mantle Network (EVM L2) — Sepolia testnet  

---

## Environment Variables

See [`.env.example`](.env.example) for the complete list.

---

## Roadmap

### Phase 1 — Core Architecture (in progress)
- [x] Real-time on-chain scanner (Mantle blocks, whale transfers, protocol interactions)
- [x] 3-provider AI fallback chain (OpenAI → Groq → AltLLM)
- [x] Paper trading engine ($10K virtual capital)
- [x] Live dashboard + Telegram alerts
- [ ] **Strategy layer** — RSI, Volume Anomaly, Nostalgia patterns
- [ ] **WhaleScore** — mathematical scoring of whale activity
- [ ] **AI arbiter** — strategies compute for free, AI only says YES/NO
- [ ] **Database (SQLite)** — persistent history for all users

### Phase 2 — Infrastructure
- [ ] Docker: single `docker-compose up`
- [ ] MetaMask wallet auth (browser-based, no .env keys)
- [ ] UI fixes: theme toggle, refresh, reconnect

### Phase 3 — Sponsor APIs (awaiting Twitter restore)
- [ ] Nansen AI — whale intelligence
- [ ] Elfa AI — social sentiment
- [ ] Surf AI — additional AI compute
- [ ] Orbit AI — agent tooling

### Phase 4 — Production
- [ ] Real DEX trading on Mantle (user's own wallet)
- [ ] Backtesting dashboard
- [ ] Strategy leaderboard

---

## License

MIT

---

<p align="center">
  Built with ☕ and ❤️ for <a href="https://dorahacks.io/hackathon/mantle-turing-test">Mantle Turing Test Hackathon 2026</a> • Phase II: AI Awakening
</p>
