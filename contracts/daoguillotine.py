# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

# =============================================================================
#  daoguillotine.py - DAOGuillotine: Decentralized Contributor Payout Auditor
#  GenLayer Intelligent Contract (v0.2.16)
# =============================================================================

from genlayer import *
import json

class UserError(Exception):
    pass

def to_address(val) -> Address:
    """
    Ensures input addresses are represented as pure Address structures,
    protecting against string/int input deserialization issues in GenLayer Studio UI.
    """
    if isinstance(val, Address):
        return val
    if isinstance(val, int):
        return Address(f"0x{val:040x}")
    if isinstance(val, str):
        if val.startswith("0x"):
            return Address(val)
        try:
            return Address(f"0x{int(val):040x}")
        except Exception:
            return Address(val)
    return Address(str(val))

class Contract(gl.Contract):
    """
    DAOGuillotine
    =============
    Holds contributor salary/bounties in escrow bound to shared acceptance criteria.
    Before payday, contributor submits authenticated work proof URL and DAO can submit counter-evidence.
    GenLayer AI validators cross-examine deliverables against acceptance criteria & counter-evidence.
    If effort is insufficient or criteria breached (is_slashed = true), salary is slashed to DAO treasury.
    Includes timeout recovery path allowing DAO to reclaim escrowed funds if abandoned or failed.
    """

    # Monotonic payroll counter
    payrolls_count:                   bigint

    # Storage Mappings (Pre-initialized by the VM)
    payroll_dao:                      TreeMap[str, Address]
    payroll_contributor:              TreeMap[str, Address]
    payroll_amount:                   TreeMap[str, bigint]
    payroll_status:                   TreeMap[str, str]       # "ACTIVE", "SLASHED", "PAID", "FAILED", "RECLAIMED"
    payroll_acceptance_criteria_url:  TreeMap[str, str]       # Agreed deliverables policy URL
    payroll_work_proof_url:           TreeMap[str, str]       # Contributor submitted proof URL
    payroll_counter_evidence_url:     TreeMap[str, str]       # DAO challenge counter-evidence URL
    payroll_is_slashed:               TreeMap[str, bool]
    payroll_effort_score:             TreeMap[str, bigint]    # 0 to 100
    payroll_audit_report:             TreeMap[str, str]

    # -------------------------------------------------------------------
    # CONSTRUCTOR
    # -------------------------------------------------------------------
    def __init__(self) -> None:
        self.payrolls_count = bigint(0)

    # -------------------------------------------------------------------
    # PUBLIC WRITE: CREATE PAYROLL ESCROW WITH ACCEPTANCE CRITERIA (BY DAO)
    # -------------------------------------------------------------------
    @gl.public.write.payable
    def create_payroll(self, contributor: Address, acceptance_criteria_url: str = "") -> int:
        """
        DAO locks native GEN tokens as salary/bounty, specifying contributor and shared acceptance criteria URL.
        """
        amount = gl.message.value
        if amount <= bigint(0):
            raise UserError("You must lock a positive GEN salary amount.")

        contributor_clean = to_address(contributor)
        if str(contributor_clean) == "0x0000000000000000000000000000000000000000":
            raise UserError("Invalid contributor address.")

        criteria_clean = acceptance_criteria_url.strip()
        if len(criteria_clean) > 0:
            crit_lower = criteria_clean.lower()
            if not (crit_lower.startswith("http://") or crit_lower.startswith("https://")):
                raise UserError("Invalid acceptance criteria URL format. Must start with http:// or https://")
        else:
            criteria_clean = "https://daoguillotine-app.vercel.app/default_acceptance_criteria.txt"

        pid = self.payrolls_count
        pid_str = str(pid)
        dao = to_address(gl.message.sender_address)

        self.payroll_dao[pid_str] = dao
        self.payroll_contributor[pid_str] = contributor_clean
        self.payroll_amount[pid_str] = amount
        self.payroll_status[pid_str] = "ACTIVE"
        self.payroll_acceptance_criteria_url[pid_str] = criteria_clean
        self.payroll_work_proof_url[pid_str] = ""
        self.payroll_counter_evidence_url[pid_str] = ""
        self.payroll_is_slashed[pid_str] = False
        self.payroll_effort_score[pid_str] = bigint(0)
        self.payroll_audit_report[pid_str] = "Awaiting claim work proof URL submission."

        self.payrolls_count = pid + bigint(1)
        return int(pid)

    # -------------------------------------------------------------------
    # PUBLIC WRITE: SUBMIT COUNTER-EVIDENCE (CHALLENGE PATH BY DAO)
    # -------------------------------------------------------------------
    @gl.public.write
    def submit_counter_evidence(self, payroll_id: int, counter_evidence_url: str) -> None:
        """
        DAO Admin attaches counter-evidence (e.g. dispute report, bug log) to challenge contributor claims.
        """
        pid_str = str(payroll_id)
        if payroll_id < 0 or bigint(payroll_id) >= self.payrolls_count:
            raise UserError("Payroll record does not exist.")

        status = self.payroll_status.get(pid_str, "ACTIVE")
        if status != "ACTIVE" and status != "FAILED":
            raise UserError("Payroll is not in active or failed state for counter-evidence submission.")

        sender = to_address(gl.message.sender_address)
        dao = to_address(self.payroll_dao.get(pid_str, Address("0x0000000000000000000000000000000000000000")))
        if str(sender) != str(dao):
            raise UserError("Only the designated DAO admin can submit counter-evidence.")

        clean_url = counter_evidence_url.strip()
        if len(clean_url) == 0:
            raise UserError("Counter-evidence URL cannot be empty.")

        url_lower = clean_url.lower()
        if not (url_lower.startswith("http://") or url_lower.startswith("https://")):
            raise UserError("Invalid counter-evidence URL format. Must start with http:// or https://")

        # Authorized Domain Check
        if not (url_lower.startswith("https://daoguillotine-app.vercel.app/") or
                url_lower.startswith("https://github.com/") or
                url_lower.startswith("https://gitlab.com/") or
                url_lower.startswith("https://status.vendor.com/") or
                url_lower.startswith("http://localhost:5173/")):
            raise UserError("Unauthorized counter-evidence domain origin.")

        self.payroll_counter_evidence_url[pid_str] = clean_url
        self.payroll_audit_report[pid_str] = "DAO counter-evidence attached. Ready for AI audit."

    # -------------------------------------------------------------------
    # PUBLIC WRITE: REQUEST SALARY / TRIGGER AUDIT (WITH COUNTER EVIDENCE)
    # -------------------------------------------------------------------
    @gl.public.write
    def request_salary_and_audit(self, payroll_id: int, work_proof_url: str, counter_evidence_url: str = "") -> None:
        """
        Contributor or DAO triggers salary audit by providing work proof URL and optional counter-evidence.
        GenLayer AI nodes scrape acceptance criteria, work proof, and counter-evidence for cross-examination.
        """
        pid_str = str(payroll_id)
        if payroll_id < 0 or bigint(payroll_id) >= self.payrolls_count:
            raise UserError("Payroll record does not exist.")

        status = self.payroll_status.get(pid_str, "ACTIVE")
        if status != "ACTIVE" and status != "FAILED":
            raise UserError("Payroll is not in active or failed state.")

        # Access Control: Authenticate contributor or DAO admin
        sender = to_address(gl.message.sender_address)
        contributor = to_address(self.payroll_contributor.get(pid_str, Address("0x0000000000000000000000000000000000000000")))
        dao = to_address(self.payroll_dao.get(pid_str, Address("0x0000000000000000000000000000000000000000")))

        if str(sender) != str(contributor) and str(sender) != str(dao):
            raise UserError("Only the designated contributor or DAO admin can request salary audit.")

        if len(work_proof_url.strip()) == 0:
            raise UserError("Work proof URL cannot be empty.")

        url_lower = work_proof_url.lower().strip()
        if not (url_lower.startswith("http://") or url_lower.startswith("https://")):
            raise UserError("Invalid work proof URL format. Must start with http:// or https://")

        # Domain Origin Safeguard
        if not (url_lower.startswith("https://daoguillotine-app.vercel.app/") or
                url_lower.startswith("https://github.com/") or
                url_lower.startswith("https://gitlab.com/") or
                url_lower.startswith("https://status.vendor.com/") or
                url_lower.startswith("http://localhost:5173/")):
            raise UserError("Unauthorized work proof domain origin.")

        if len(counter_evidence_url.strip()) > 0:
            ce_lower = counter_evidence_url.lower().strip()
            if not (ce_lower.startswith("http://") or ce_lower.startswith("https://")):
                raise UserError("Invalid counter-evidence URL format.")
            if not (ce_lower.startswith("https://daoguillotine-app.vercel.app/") or
                    ce_lower.startswith("https://github.com/") or
                    ce_lower.startswith("https://gitlab.com/") or
                    ce_lower.startswith("https://status.vendor.com/") or
                    ce_lower.startswith("http://localhost:5173/")):
                raise UserError("Unauthorized counter-evidence domain origin.")
            self.payroll_counter_evidence_url[pid_str] = counter_evidence_url.strip()

        # Update status and save work proof URL
        self.payroll_work_proof_url[pid_str] = work_proof_url.strip()
        self.payroll_status[pid_str] = "ACTIVE"
        self.payroll_audit_report[pid_str] = "Auditing report text. Inspecting deliverables against criteria..."

        acceptance_criteria_url = self.payroll_acceptance_criteria_url.get(pid_str, "")
        final_counter_evidence_url = self.payroll_counter_evidence_url.get(pid_str, "")

        # Non-Deterministic Consensus Function
        def leader_fn() -> str:
            # 1. Fetch Acceptance Criteria
            criteria_text = "Standard DAO Deliverables: Complete assigned tasks with tangible outputs."
            if len(acceptance_criteria_url) > 0:
                try:
                    raw_crit = gl.nondet.web.render(acceptance_criteria_url)
                    criteria_text = raw_crit.decode('utf-8', errors='ignore').strip() if isinstance(raw_crit, bytes) else str(raw_crit).strip()
                except Exception as e:
                    criteria_text = f"Default criteria (web load warning: {str(e)})"

            # 2. Fetch Work Proof
            try:
                raw_data = gl.nondet.web.render(work_proof_url)
                if isinstance(raw_data, bytes):
                    text = raw_data.decode('utf-8', errors='ignore').strip()
                else:
                    text = str(raw_data).strip()
            except Exception as e:
                return json.dumps({
                    "error": "URL_LOAD_FAILED",
                    "is_slashed": True,
                    "effort_score": 0,
                    "audit_report": f"Auditor could not load the work report at {work_proof_url}: {str(e)}"
                })

            if len(text) < 15:
                return json.dumps({
                    "error": "EMPTY_REPORT",
                    "is_slashed": True,
                    "effort_score": 0,
                    "audit_report": "The work report page appeared to be empty or unparseable. Cannot verify claims."
                })

            # 3. Fetch Counter-Evidence if present
            counter_text = "None submitted by DAO."
            if len(final_counter_evidence_url) > 0:
                try:
                    raw_ce = gl.nondet.web.render(final_counter_evidence_url)
                    counter_text = raw_ce.decode('utf-8', errors='ignore').strip() if isinstance(raw_ce, bytes) else str(raw_ce).strip()
                except Exception:
                    counter_text = f"Counter-evidence submitted at {final_counter_evidence_url} (Could not load body)."

            excerpt_criteria = criteria_text[:2000]
            excerpt_work = text[:5000]
            excerpt_counter = counter_text[:2000]

            # 4. AI Tech Lead Prompt
            prompt = f"""You are a Ruthless Technical Lead acting as an Auditor in a DAO payroll system.
Your job is to examine work reports against agreed acceptance criteria and optional DAO counter-evidence.
Identify "fake work", corporate fluff, meeting-spam, or unfulfilled acceptance criteria.
Separate concrete deliverables (written code, PRs, graphics, finished documents, deployed systems) from filler ("Attended meetings," "Telegram chat", "GM tweets").

AGREED ACCEPTANCE CRITERIA:
\"\"\"
{excerpt_criteria}
\"\"\"

CONTRIBUTOR WORK PROOF TEXT ({work_proof_url}):
\"\"\"
{excerpt_work}
\"\"\"

DAO COUNTER-EVIDENCE DISPUTE TEXT:
\"\"\"
{excerpt_counter}
\"\"\"

EVALUATION INSTRUCTIONS:
1. Cross-examine the contributor work proof against agreed acceptance criteria and DAO counter-evidence.
2. Calculate an "effort_score" from 0 to 100 based on tangible criteria fulfillment.
3. If "effort_score" is less than 50 or criteria breached, "is_slashed" MUST be true. If 50 or above, "is_slashed" should be false.
4. Write a concise, direct audit report.

Respond ONLY as a single valid JSON object:
{{
  "is_slashed": boolean,
  "effort_score": integer,
  "audit_report": "string"
}}
"""

            try:
                raw_output = gl.nondet.exec_prompt(prompt)
                raw_str = raw_output.decode('utf-8', errors='ignore').strip() if isinstance(raw_output, bytes) else str(raw_output).strip()
            except Exception as e:
                return json.dumps({
                    "error": f"LLM_EXECUTION_FAILED: {str(e)}",
                    "is_slashed": True,
                    "effort_score": 0,
                    "audit_report": "LLM technical lead failed to audit the work."
                })

            cleaned = raw_str.strip()
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
                raw_slashed = parsed.get("is_slashed")

                # STRICT BOOLEAN TYPE VALIDATION
                if not isinstance(raw_slashed, bool):
                    return json.dumps({
                        "error": "INVALID_BOOLEAN_TYPE",
                        "is_slashed": True,
                        "effort_score": 0,
                        "audit_report": "AI Auditor verdict contained a non-boolean value for is_slashed."
                    })

                is_slashed = raw_slashed
                score = int(parsed.get("effort_score", 0))
                report = str(parsed.get("audit_report", "No audit details.")).strip()

                if score < 0: score = 0
                if score > 100: score = 100

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
            Semantic HR Validator: Enforces consensus on slashing.
            Returns False on any leader or validator error to fail closed.
            Requires strict JSON boolean validation.
            """
            try:
                leader_str = leader_result.decode('utf-8', errors='ignore') if isinstance(leader_result, bytes) else str(leader_result)
                l_start = leader_str.find('{')
                l_end = leader_str.rfind('}')
                if l_start == -1 or l_end == -1 or l_start > l_end:
                    return False
                cleaned_leader = leader_str[l_start:l_end+1]
                leader_data = json.loads(cleaned_leader)
            except Exception:
                return False

            if "error" in leader_data:
                return False  # Reject consensus on leader error (Fail closed)

            # STRICT BOOLEAN CHECK FOR LEADER RESULT
            leader_slashed_raw = leader_data.get("is_slashed")
            if not isinstance(leader_slashed_raw, bool):
                return False

            validator_raw = leader_fn()
            try:
                val_str = validator_raw.decode('utf-8', errors='ignore') if isinstance(validator_raw, bytes) else str(validator_raw)
                v_start = val_str.find('{')
                v_end = val_str.rfind('}')
                if v_start == -1 or v_end == -1 or v_start > v_end:
                    return False
                cleaned_val = val_str[v_start:v_end+1]
                validator_data = json.loads(cleaned_val)
            except Exception:
                return False  # Reject consensus on validator parse error

            if "error" in validator_data:
                return False  # Reject consensus if validator encountered error

            # STRICT BOOLEAN CHECK FOR VALIDATOR RESULT
            val_slashed_raw = validator_data.get("is_slashed")
            if not isinstance(val_slashed_raw, bool):
                return False

            leader_slashed = leader_slashed_raw
            validator_slashed = val_slashed_raw

            return leader_slashed == validator_slashed

        # Execute Consensus on GenLayer VM
        consensus_json = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)

        try:
            cons_str = consensus_json.decode('utf-8', errors='ignore') if isinstance(consensus_json, bytes) else str(consensus_json)
            cons_start = cons_str.find('{')
            cons_end = cons_str.rfind('}')
            if cons_start == -1 or cons_end == -1 or cons_start > cons_end:
                raise ValueError("No JSON object found")
            cleaned_cons = cons_str[cons_start:cons_end+1]
            res = json.loads(cleaned_cons)
        except Exception:
            self.payroll_status[pid_str] = "FAILED"
            self.payroll_audit_report[pid_str] = "Consensus outcome was unparseable JSON."
            return

        if "error" in res:
            self.payroll_status[pid_str] = "FAILED"
            self.payroll_audit_report[pid_str] = f"Audit failed: {res.get('error')}. Info: {res.get('audit_report')}"
            return

        # STRICT SETTLEMENT PATH BOOLEAN VALIDATION
        settle_slashed_raw = res.get("is_slashed")
        if not isinstance(settle_slashed_raw, bool):
            self.payroll_status[pid_str] = "FAILED"
            self.payroll_audit_report[pid_str] = "Audit Failed: Invalid non-boolean value for is_slashed in settlement path."
            return

        is_slashed = settle_slashed_raw
        score = int(res.get("effort_score", 0))
        report = str(res.get("audit_report", "Audit processed."))

        self.payroll_is_slashed[pid_str] = is_slashed
        self.payroll_effort_score[pid_str] = bigint(score)
        self.payroll_audit_report[pid_str] = report

        amount = self.payroll_amount.get(pid_str, bigint(0))
        if amount <= bigint(0):
            raise UserError("No salary funds locked in this payroll.")

        # Reentrancy Protection
        self.payroll_amount[pid_str] = bigint(0)

        # Execute payout or DAO refund using SDK account-transfer API
        if is_slashed:
            # Funds returned to DAO treasury
            self.payroll_status[pid_str] = "SLASHED"
            other_dao = gl.get_contract_at(dao)
            other_dao.emit_transfer(value=bigint(amount))
        else:
            # Salary released to contributor
            self.payroll_status[pid_str] = "PAID"
            other_contributor = gl.get_contract_at(contributor)
            other_contributor.emit_transfer(value=bigint(amount))

    # Backward compatibility wrapper method
    @gl.public.write
    def request_salary(self, payroll_id: int, work_proof_url: str) -> None:
        """
        Backward-compatible method calling request_salary_and_audit.
        """
        self.request_salary_and_audit(payroll_id, work_proof_url, "")

    # -------------------------------------------------------------------
    # PUBLIC WRITE: TIMEOUT RECOVERY PATH (BY DAO)
    # -------------------------------------------------------------------
    @gl.public.write
    def reclaim_timed_out_payroll(self, payroll_id: int) -> None:
        """
        Allows the DAO to recover locked GEN deposit if the payroll failed audit
        or if the contributor abandoned the claim.
        """
        pid_str = str(payroll_id)
        if payroll_id < 0 or bigint(payroll_id) >= self.payrolls_count:
            raise UserError("Payroll record does not exist.")

        status = self.payroll_status.get(pid_str, "")
        if status != "ACTIVE" and status != "FAILED":
            raise UserError("Payroll is not in active or failed state for timeout recovery.")

        sender = to_address(gl.message.sender_address)
        dao = to_address(self.payroll_dao.get(pid_str, Address("0x0000000000000000000000000000000000000000")))
        if str(sender) != str(dao):
            raise UserError("Only the designated DAO admin can reclaim timed out payroll funds.")

        amount = self.payroll_amount.get(pid_str, bigint(0))
        if amount <= bigint(0):
            raise UserError("Payroll has no locked funds to reclaim.")

        self.payroll_amount[pid_str] = bigint(0)
        self.payroll_status[pid_str] = "RECLAIMED"
        self.payroll_audit_report[pid_str] = "DAO admin reclaimed escrowed funds via timeout recovery path."

        gl.get_contract_at(dao).emit_transfer(value=bigint(amount))

    # -------------------------------------------------------------------
    # READ-ONLY VIEW METHODS
    # -------------------------------------------------------------------
    @gl.public.view
    def get_payroll(self, payroll_id: int) -> str:
        """
        Returns a JSON-serialized representation of a payroll escrow.
        """
        pid_str = str(payroll_id)
        if payroll_id < 0 or bigint(payroll_id) >= self.payrolls_count:
            return "{}"

        dao = to_address(self.payroll_dao.get(pid_str, Address("0x0000000000000000000000000000000000000000")))
        contributor = to_address(self.payroll_contributor.get(pid_str, Address("0x0000000000000000000000000000000000000000")))
        amount = self.payroll_amount.get(pid_str, bigint(0))
        status = self.payroll_status.get(pid_str, "ACTIVE")
        crit_url = self.payroll_acceptance_criteria_url.get(pid_str, "")
        proof = self.payroll_work_proof_url.get(pid_str, "")
        counter = self.payroll_counter_evidence_url.get(pid_str, "")
        slashed = bool(self.payroll_is_slashed.get(pid_str, False))
        score = int(self.payroll_effort_score.get(pid_str, bigint(0)))
        report = self.payroll_audit_report.get(pid_str, "")

        return json.dumps({
            "id": payroll_id,
            "dao": str(dao),
            "contributor": str(contributor),
            "amount": int(amount),
            "status": status,
            "acceptance_criteria_url": crit_url,
            "work_proof_url": proof,
            "counter_evidence_url": counter,
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
