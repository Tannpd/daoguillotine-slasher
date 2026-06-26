# DAOGuillotine — Decentralized Contributor Payout Auditor

A smart contract for DAOs that holds contributor salaries in escrow. Before a payday, the contributor must submit a link to their work report. The AI acts as a "Ruthless HR Auditor" scanning the report to detect fluff and meeting spam. If effort is insufficient (is_slashed = true), the salary is slashed and refunded to the DAO treasury. Otherwise, the salary is released to the contributor.

## 🎯 The Pitch
**"Why DAOGuillotine DIES without GenLayer."**

Traditional smart contracts (like Ethereum EVM) are fully deterministic and isolated. They cannot fetch web pages natively and cannot evaluate natural language evidence (such as GitHub pull requests, Notion documents, or weekly work reports). To build this on EVM, you would need complex, expensive, and highly centralized Web2 oracles to scrape pages and call LLMs.

**GenLayer solves this entirely.** DAOGuillotine runs natively on GenLayer, calling `gl.nondet.web.render` to extract evidence text directly from a URL, and `gl.nondet.exec_prompt` to act as an impartial technical lead auditor. By wrapping this in GenLayer's consensus mechanism (`run_nondet_unsafe`), multiple validator nodes independently scrape the evidence and run the LLM. They verify consensus on a core slashing boolean on-chain. **Without GenLayer, DAOGuillotine is mathematically impossible to implement in a decentralized manner.**

---

## 🛠️ Project Structure
```
D:\Gen\DAOGuillotine\
├── contracts/
│   └── daoguillotine.py  # GenLayer Intelligent Contract (v0.2.16)
├── frontend/
│   ├── src/
│   │   ├── App.jsx       # Aggressive Cyberpunk Terminal UI
│   │   ├── index.css     # CSS rules (glowing scanlines, CRT screens, steel borders)
│   │   ├── useDAOGuillotine.js # Hook for GenLayer StudioNet integration
│   │   └── main.jsx
│   ├── index.html        # Entry HTML
│   ├── vite.config.js    # Dev server configuration
│   ├── .env              # Environment config containing contract address
│   └── package.json      # React + genlayer-js client libraries
└── README.md             # Project Documentation
```

---

## 🚀 Step-by-Step Deployment Guide

### Step 1: Deploy the Smart Contract using GenLayer Studio
1. Open the **GenLayer Studio** (usually running at [http://localhost:3000](http://localhost:3000) or the official studio web interface).
2. Create a new file named `daoguillotine.py` in the Studio contract explorer.
3. Copy the contents of `D:\Gen\DAOGuillotine\contracts\daoguillotine.py` and paste them into the editor in GenLayer Studio.
4. Click **Compile** to verify the syntax and dependencies.
5. Under the **Deploy** panel, click **Deploy Contract**.
6. Once deployed, note down the generated contract address (e.g. `0x0F0D...`).

### Step 2: Configure the Frontend
1. Open the `.env` file located at `D:\Gen\DAOGuillotine\frontend\.env`.
2. Insert your deployed contract address:
   ```env
   VITE_CONTRACT_ADDRESS="0xYOUR_DEPLOYED_CONTRACT_ADDRESS_HERE"
   ```
3. Save the file.

### Step 3: Run the Frontend App
1. Open your terminal in the frontend directory:
   ```powershell
   cd D:\Gen\DAOGuillotine\frontend
   ```
2. Start the local development server:
   ```powershell
   npm run dev
   ```
3. Open the printed local URL (typically [http://localhost:5173](http://localhost:5173)) in your web browser.
