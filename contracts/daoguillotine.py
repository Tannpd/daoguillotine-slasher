# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

# =============================================================================
#  daoguillotine.py — DAOGuillotine: Decentralized Contributor Payout Auditor
#  GenLayer Intelligent Contract (v0.2.16)
# =============================================================================

from genlayer import *
import json

class Contract(gl.Contract):
    """
    DAOGuillotine
    =============
    Holds contributor salary/bounties in escrow. Before a payday, the contributor
    submits a work report URL. The AI acts as a ruthless tech lead auditing report text,
    punishing corporate fluff and meeting spam. If effort is insufficient (is_slashed = true),
    the salary is slashed and refunded to the DAO. If acceptable, it pays out.
    """

    # Monotonic payroll counter
    payrolls_count:               u64

    # Storage Mappings (Pre-initialized by the VM; do not reassign in __init__)
    payroll_dao:                  TreeMap[u64, Address]
    payroll_contributor:          TreeMap[u64, Address]
    payroll_amount:               TreeMap[u64, u256]
    payroll_status:               TreeMap[u64, str]       # "ACTIVE", "SLASHED", "PAID", "FAILED"
    payroll_work_proof_url:       TreeMap[u64, str]
    payroll_is_slashed:           TreeMap[u64, bool]
    payroll_effort_score:         TreeMap[u64, u256]      # 0 to 100
    payroll_audit_report:         TreeMap[u64, str]

    # ═══════════════════════════════════════════════════════════════════
    # CONSTRUCTOR
    # ═══════════════════════════════════════════════════════════════════
    def __init__(self) -> None:
        """
        Constructor. Standard GenLayer initialization.
        """
        self.payrolls_count = 0

    # ═══════════════════════════════════════════════════════════════════
    # PUBLIC WRITE: CREATE PAYROLL ESCROW (BY DAO)
    # ═══════════════════════════════════════════════════════════════════
    @gl.public.write
    def create_payroll(self, contributor: Address) -> int:
        """
        DAO calls this, locks native GEN tokens as a salary/bounty, and specifies the contributor.
        """
        amount = int(gl.message.value)
        if amount <= 0:
            raise UserError("You must lock a positive GEN salary amount.")

        pid = self.payrolls_count

        self.payroll_dao[pid] = gl.message.sender_address
        self.payroll_contributor[pid] = contributor
        self.payroll_amount[pid] = amount
        self.payroll_status[pid] = "ACTIVE"
        self.payroll_work_proof_url[pid] = ""
        self.payroll_is_slashed[pid] = False
        self.payroll_effort_score[pid] = 0
        self.payroll_audit_report[pid] = "Awaiting claim and work proof URL submission."

        self.payrolls_count = int(pid) + 1
        return int(pid)

    # ═══════════════════════════════════════════════════════════════════
    # PUBLIC WRITE: REQUEST SALARY / TRIGGER AUDIT (BY CONTRIBUTOR)
    # ═══════════════════════════════════════════════════════════════════
    @gl.public.write
    def request_salary(self, payroll_id: int, work_proof_url: str) -> None:
        """
        Contributor triggers this by submitting a link to their work report.
        The AI scans and audits the work, executing a payout or slash/refund.
        """
        if payroll_id < 0 or payroll_id >= int(self.payrolls_count):
            raise UserError("Payroll record does not exist.")

        status = self.payroll_status.get(payroll_id, "ACTIVE")
        if status != "ACTIVE" and status != "FAILED":
            raise UserError("Payroll is not in active or failed state.")

        contributor = self.payroll_contributor.get(payroll_id, Address("0x0000000000000000000000000000000000000000"))
        if gl.message.sender_address != contributor:
            raise UserError("Only the designated contributor can request salary.")

        if len(work_proof_url.strip()) == 0:
            raise UserError("Work proof URL cannot be empty.")

        # Update status and save work proof URL
        self.payroll_work_proof_url[payroll_id] = work_proof_url.strip()
        self.payroll_status[payroll_id] = "ACTIVE" # Reset if failed previously
        self.payroll_audit_report[payroll_id] = "Auditing report text. Inspecting deliverables..."

        # Non-Deterministic Consensus Function
        def leader_fn() -> str:
            # 1. Fetch web contents
            failed = False
            try:
                raw_text = gl.nondet.web.render(work_proof_url)
                text = raw_text.strip()
            except Exception as e:
                failed = True
                text = f"ERROR: Failed to fetch report: {str(e)}"

            if failed or len(text) < 30:
                return json.dumps({
                    "error": "URL_LOAD_FAILED",
                    "is_slashed": True,
                    "effort_score": 0,
                    "audit_report": f"Auditor could not load the work report at {work_proof_url} or contents were empty."
                })

            excerpt = text[:6000]

            # 2. AI Tech Lead Prompt
            prompt = f"""You are a Ruthless Technical & Business Lead acting as an Auditor in a DAO payroll system.
Your job is to examine work reports and identify "fake work", corporate fluff, meeting-spam, and low-effort participation. 
You must separate concrete deliverables (such as written code, PRs, designed graphics, finished documents, deployed systems) from general filler (such as "Attended meetings," "Exchanged messages on Telegram," "Tweeted GM", "Did research" without any links or outputs).

Severely punish corporate fluff. If a contributor spends their time on "organizing meetings" or "discussing ideas" with no concrete output, set "is_slashed" to true.

Work Proof URL: {work_proof_url}
Scraped Work Proof Text:
--- START WORK REPORT ---
{excerpt}
--- END WORK REPORT ---

Evaluate:
1. Did the contributor complete concrete, tangible deliverables?
2. Is the report filled with corporate fluff, meetings, or low-effort actions?
3. Calculate an "effort_score" from 0 to 100 (where 0 means zero real deliverables/total fluff, and 100 means massive tangible deliverables).
4. If "effort_score" is less than 50, "is_slashed" MUST be true. If "effort_score" is 50 or above, "is_slashed" should be false.
5. Write a concise, direct, and critical "Audit Report" (audit_report) summarizing their effort.

Your output MUST be a single, valid JSON object with EXACTLY the following keys:
{{
  "is_slashed": true | false,
  "effort_score": <int between 0 and 100>,
  "audit_report": "<2-3 sentences of direct and honest audit review>"
}}
Do NOT wrap the JSON in markdown code blocks. Do NOT add extra text or conversation. Only return raw JSON."""

            try:
                raw_output = gl.nondet.exec_prompt(prompt)
            except Exception as e:
                return json.dumps({
                    "error": f"LLM_EXECUTION_FAILED: {str(e)}",
                    "is_slashed": True,
                    "effort_score": 0,
                    "audit_report": "LLM technical lead failed to audit the work."
                })

            cleaned = raw_output.strip()
            # Clean markdown code blocks if present
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                inner = []
                for line in lines[1:]:
                    if line.strip() == "```":
                        break
                    inner.append(line)
                cleaned = "\n".join(inner).strip()

            try:
                parsed = json.loads(cleaned)
                is_slashed = bool(parsed.get("is_slashed", True))
                score = int(parsed.get("effort_score", 0))
                report = str(parsed.get("audit_report", "No audit details.")).strip()

                if score < 0: score = 0
                if score > 100: score = 100

                # Enforce mapping consistency
                if score < 50:
                    is_slashed = True

                return json.dumps({
                    "is_slashed": is_slashed,
                    "effort_score": score,
                    "audit_report": report[:1000]
                })
            except Exception as e:
                return json.dumps({
                    "error": f"JSON_PARSE_FAILED: {str(e)}",
                    "is_slashed": True,
                    "effort_score": 0,
                    "audit_report": f"Failed to parse AI output. Raw response: {cleaned}"
                })

        def validator_fn(leader_result: str) -> bool:
            """
            Semantic HR Validator (MANDATORY):
            Enforces "Core Consensus" on the boolean slashing outcome:
            leader["is_slashed"] == validator["is_slashed"]
            """
            try:
                leader_data = json.loads(leader_result)
            except Exception:
                return False

            if "error" in leader_data:
                allowed_errors = {"URL_LOAD_FAILED", "LLM_EXECUTION_FAILED", "JSON_PARSE_FAILED"}
                return any(err in str(leader_data.get("error", "")) for err in allowed_errors)

            validator_raw = leader_fn()
            try:
                validator_data = json.loads(validator_raw)
            except Exception:
                return True  # Abstain on validator parsing error

            if "error" in validator_data:
                return True

            leader_slashed = bool(leader_data.get("is_slashed", True))
            validator_slashed = bool(validator_data.get("is_slashed", True))

            # The core consensus checks if nodes agree on the SLASH outcome
            return leader_slashed == validator_slashed

        # Execute Consensus on GenLayer VM
        consensus_json = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)

        try:
            res = json.loads(consensus_json)
        except Exception:
            self.payroll_status[payroll_id] = "FAILED"
            self.payroll_audit_report[payroll_id] = "Consensus outcome was unparseable JSON."
            return

        if "error" in res:
            self.payroll_status[payroll_id] = "FAILED"
            self.payroll_audit_report[payroll_id] = f"Audit failed: {res.get('error')}. Info: {res.get('audit_report')}"
            return

        is_slashed = bool(res.get("is_slashed", True))
        score = int(res.get("effort_score", 0))
        report = str(res.get("audit_report", "Audit processed."))

        self.payroll_is_slashed[payroll_id] = is_slashed
        self.payroll_effort_score[payroll_id] = score
        self.payroll_audit_report[payroll_id] = report

        amount = int(self.payroll_amount.get(payroll_id, 0))
        if amount <= 0:
            raise UserError("No salary funds locked in this payroll.")

        # Reentrancy Protection
        self.payroll_amount[payroll_id] = 0

        dao = self.payroll_dao.get(payroll_id, Address("0x0000000000000000000000000000000000000000"))

        if is_slashed:
            # Funds returned to DAO treasury
            self.payroll_status[payroll_id] = "SLASHED"
            other_dao = gl.get_contract_at(dao)
            other_dao.emit_transfer(value=u256(amount))
        else:
            # Salary released to contributor
            self.payroll_status[payroll_id] = "PAID"
            other_contributor = gl.get_contract_at(contributor)
            other_contributor.emit_transfer(value=u256(amount))

    # ═══════════════════════════════════════════════════════════════════
    # READ-ONLY VIEW METHODS
    # ═══════════════════════════════════════════════════════════════════
    @gl.public.view
    def get_payroll(self, payroll_id: int) -> str:
        """
        Returns a JSON-serialized representation of a payroll escrow.
        """
        if payroll_id < 0 or payroll_id >= int(self.payrolls_count):
            return "{}"

        dao = self.payroll_dao.get(payroll_id, Address("0x0000000000000000000000000000000000000000"))
        contributor = self.payroll_contributor.get(payroll_id, Address("0x0000000000000000000000000000000000000000"))
        amount = int(self.payroll_amount.get(payroll_id, 0))
        status = self.payroll_status.get(payroll_id, "ACTIVE")
        proof = self.payroll_work_proof_url.get(payroll_id, "")
        slashed = bool(self.payroll_is_slashed.get(payroll_id, False))
        score = int(self.payroll_effort_score.get(payroll_id, 0))
        report = self.payroll_audit_report.get(payroll_id, "")

        return json.dumps({
            "id": payroll_id,
            "dao": str(dao),
            "contributor": str(contributor),
            "amount": amount,
            "status": status,
            "work_proof_url": proof,
            "is_slashed": slashed,
            "effort_score": score,
            "audit_report": report
        })

    @gl.public.view
    def get_payrolls_count(self) -> int:
        """
        Returns the total number of payroll escrows created.
        """
        return int(self.payrolls_count)
