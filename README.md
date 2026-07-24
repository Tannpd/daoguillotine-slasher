# DAOGuillotine — Decentralized Contributor Payout Auditor

DAOGuillotine is an intelligent escrow contract for DAOs that holds contributor salaries in escrow. Before a payday, the contributor submits a link to their work report. GenLayer AI nodes act as a "Ruthless HR & Tech Auditor", scanning the report to detect fluff and meeting spam. If effort is insufficient (`is_slashed = true`), the salary is slashed and refunded to the DAO treasury. Otherwise, the salary is released to the contributor.

**Deployed Contract Address (StudioNet)**: `0x4b9bAb2d12B6003206Fb7DFB06fB8a81B482B41b`  
**Live Vercel Application**: [https://daoguillotine-slasher.vercel.app/](https://daoguillotine-slasher.vercel.app/)  
**GitHub Repository**: [https://github.com/Tannpd/daoguillotine-slasher](https://github.com/Tannpd/daoguillotine-slasher)

---

## 🎯 The Pitch
**"Why DAOGuillotine DIES without GenLayer."**

Traditional smart contracts (like Ethereum EVM) are fully deterministic and isolated. They cannot fetch web pages natively and cannot evaluate natural language evidence (such as GitHub pull requests, Notion documents, or weekly work reports). To build this on EVM, you would need complex, expensive, and highly centralized Web2 oracles to scrape pages and call LLMs.

**GenLayer solves this entirely.** DAOGuillotine runs natively on GenLayer, calling `gl.nondet.web.render` to extract evidence text directly from a URL, and `gl.nondet.exec_prompt` to act as an impartial technical lead auditor. By wrapping this in GenLayer's consensus mechanism (`run_nondet_unsafe`), multiple validator nodes independently scrape the evidence and run the LLM. They verify consensus on a core slashing boolean on-chain. **Without GenLayer, DAOGuillotine is mathematically impossible to implement in a decentralized manner.**

---

## 🛡️ Key Security & Architecture Safeguards (GenLayer v0.2.16)

1. **Payable Entry Point (`create_payroll`)**:
   - Marked `@gl.public.write.payable` to accept native GEN salary/bounty deposits from DAO treasury into escrow.

2. **Unsuppressed SDK Account-Transfer API**:
   - Both payout branches (releasing salary to contributor vs. refunding slashed funds to DAO) execute using `other.emit_transfer(value=bigint(amount))` without silent error suppression (`try-except: pass`).

3. **Strict JSON Boolean Validation**:
   - Enforces explicit `isinstance(raw_slashed, bool)` checks across Leader, Validator, and Settlement paths to prevent string `"false"`/`"true"` coercion to `True`.

4. **Fail-Closed Validator Error Rejection**:
   - In `validator_fn`: returns `False` whenever leader or validator encounters a scrape, LLM, or parsing error, keeping escrow funds locked safely.

5. **Repository-Backed Unit Test Suite**:
   - Includes full unit test suite `tests/test_daoguillotine.py` covering deposit, contributor payment, DAO refund, access control, strict boolean validation, and fail-closed validator behavior (7/7 tests passing).

---

## 🛠️ Project Structure
```
D:\Gen\DAOGuillotine\
├── contracts/
│   └── daoguillotine.py      # GenLayer Intelligent Contract (v0.2.16)
├── tests/
│   └── test_daoguillotine.py # Automated unit test suite (7 tests)
├── frontend/
│   ├── src/
│   │   ├── App.jsx           # Cyberpunk Terminal UI with quick test buttons
│   │   ├── useDAOGuillotine.js # Hook with same-origin RPC CORS proxy
│   │   └── main.jsx
│   ├── public/
│   │   ├── mock_report_solid_work.txt     # Live mock solid work report
│   │   └── mock_report_fluff_meetings.txt # Live mock fluff report
│   ├── vercel.json           # Vercel same-origin RPC rewrite config
│   ├── .env                  # Environment config containing contract address
│   └── package.json          # React + genlayer-js client libraries
├── client.js                 # JS SDK client file
├── pytest.ini                # Pytest configuration
├── requirements-dev.txt      # Development dependencies
└── README.md                 # Project Documentation
```

---

## 🚀 Running Tests locally

Run the unit test suite:
```powershell
.venv\Scripts\python -m unittest tests/test_daoguillotine.py -v
```

---

## 🚀 Local Development Guide

1. Open your terminal in the frontend directory:
   ```powershell
   cd D:\Gen\DAOGuillotine\frontend
   ```
2. Start the local development server:
   ```powershell
   npm run dev
   ```
3. Open [http://localhost:5173](http://localhost:5173) in your browser.
