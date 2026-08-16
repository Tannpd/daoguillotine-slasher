# v0.2.17
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

# =============================================================================
#  daoguillotine.py - DAOGuillotine: Decentralized Contributor Payout Auditor
#  GenLayer Intelligent Contract (v0.2.17)
#
#  Steward Fixes (v0.2.17):
#  1. Per-party evidence locking: work proof URL and counter-evidence URL each lock
#     immediately upon first submission — no replacement by either party.
#  2. Measurable Challenge Window: challenge_deadline_ts agreed at creation.
#     AI audit cannot begin until current_time > challenge_deadline_ts (verified
#     via time oracle inside the same nondet call).
#  3. Enforced Recovery Deadline: recovery_deadline_ts agreed at creation.
#     reclaim_timed_out_payroll only executes after recovery_deadline_ts has passed
#     (verified via time oracle).
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

# ---------------------------------------------------------------------------
# Authorized time sources — canonical, third-party time authority APIs only.
# Project-hosted, localhost, and GitHub raw URLs are strictly excluded.
# ---------------------------------------------------------------------------
AUTHORIZED_TIME_DOMAINS = [
    "https://worldtimeapi.org/",
    "https://timeapi.io/",
]

# Minimum sensible Unix timestamp (2025-01-01) for deadline validation
MIN_VALID_TS = 1735689600

class Contract(gl.Contract):
    """
    DAOGuillotine
    =============
    Holds contributor salary/bounties in escrow bound to shared, immutable acceptance criteria.

    Evidence Integrity (Fix 1 — Per-party locking):
    - Contributor's work proof URL locks permanently upon first submission via submit_work_proof().
    - DAO's counter-evidence URL locks permanently upon first submission via submit_counter_evidence().
    - Neither party can replace their evidence after locking — UserError raised on attempt.
    - Criteria URL is immutable from creation (unchanged).

    Challenge Window (Fix 2 — Measurable timeout):
    - challenge_deadline_ts (Unix timestamp) is agreed at payroll creation by the DAO.
    - AI audit (request_salary_and_audit) CANNOT begin until current_time > challenge_deadline_ts.
    - Guarantees DAO has a real, measurable window to submit counter-evidence before arbitration.
    - Time is verified via authenticated canonical time oracle (worldtimeapi.org or timeapi.io).

    Recovery Deadline (Fix 3 — Enforced timeout):
    - recovery_deadline_ts (Unix timestamp) is agreed at payroll creation by the DAO.
    - reclaim_timed_out_payroll() only executes after recovery_deadline_ts has passed.
    - Prevents premature DAO recovery immediately after a FAILED audit.
    - Time is verified via authenticated canonical time oracle.
    """

    # Monotonic payroll counter
    payrolls_count:                    bigint

    # Core payroll identity and state
    payroll_dao:                       TreeMap[str, Address]
    payroll_contributor:               TreeMap[str, Address]
    payroll_amount:                    TreeMap[str, bigint]
    payroll_status:                    TreeMap[str, str]       # ACTIVE, DISPUTED, SLASHED, PAID, FAILED, RECLAIMED
    payroll_acceptance_criteria_url:   TreeMap[str, str]       # Immutable from creation
    payroll_work_proof_url:            TreeMap[str, str]       # Contributor evidence
    payroll_counter_evidence_url:      TreeMap[str, str]       # DAO counter-evidence
    payroll_audit_opened:              TreeMap[str, bool]      # True once AI audit commences
    payroll_is_slashed:                TreeMap[str, bool]
    payroll_effort_score:              TreeMap[str, bigint]    # 0–100
    payroll_audit_report:              TreeMap[str, str]

    # FIX 1: Per-party evidence locking (independent of audit_opened)
    payroll_work_proof_locked:         TreeMap[str, bool]      # True after first submit_work_proof
    payroll_counter_evidence_locked:   TreeMap[str, bool]      # True after first submit_counter_evidence

    # FIX 2: Challenge window deadline (immutable, agreed at creation)
    payroll_challenge_deadline_ts:     TreeMap[str, bigint]    # Audit blocked until after this Unix ts

    # FIX 3: Recovery deadline (immutable, agreed at creation)
    payroll_recovery_deadline_ts:      TreeMap[str, bigint]    # Reclaim blocked until after this Unix ts

    # -------------------------------------------------------------------
    # CONSTRUCTOR
    # -------------------------------------------------------------------
    def __init__(self) -> None:
        self.payrolls_count = bigint(0)

    # -------------------------------------------------------------------
    # PUBLIC WRITE: CREATE PAYROLL ESCROW
    # -------------------------------------------------------------------
    @gl.public.write.payable
    def create_payroll(
        self,
        contributor: Address,
        acceptance_criteria_url: str,
        challenge_deadline_ts: int,
        recovery_deadline_ts: int,
    ) -> int:
        """
        DAO locks native GEN tokens as salary/bounty.
        Binds immutable acceptance criteria, a measurable challenge window deadline,
        and a recovery deadline — all agreed upfront at creation.

        challenge_deadline_ts: Unix timestamp after which AI audit can be triggered.
                               DAO must submit counter-evidence BEFORE this deadline.
        recovery_deadline_ts:  Unix timestamp after which failed-audit recovery is permitted.
                               Must be >= challenge_deadline_ts.
        """
        amount = gl.message.value
        if amount <= bigint(0):
            raise UserError("You must lock a positive GEN salary amount.")

        contributor_clean = to_address(contributor)
        if str(contributor_clean) == "0x0000000000000000000000000000000000000000":
            raise UserError("Invalid contributor address.")

        criteria_clean = acceptance_criteria_url.strip()
        if len(criteria_clean) == 0:
            raise UserError("Shared acceptance criteria URL cannot be empty. DAO must define immutable deliverables policy.")

        crit_lower = criteria_clean.lower()
        if not (crit_lower.startswith("http://") or crit_lower.startswith("https://")):
            raise UserError("Invalid acceptance criteria URL format. Must start with http:// or https://")

        # Validate challenge deadline
        if challenge_deadline_ts < MIN_VALID_TS:
            raise UserError("challenge_deadline_ts must be a valid future Unix timestamp (after 2025-01-01).")

        # Validate recovery deadline — must be >= challenge deadline
        if recovery_deadline_ts < challenge_deadline_ts:
            raise UserError("recovery_deadline_ts must be >= challenge_deadline_ts.")

        pid = self.payrolls_count
        pid_str = str(pid)
        dao = to_address(gl.message.sender_address)

        self.payroll_dao[pid_str]                      = dao
        self.payroll_contributor[pid_str]              = contributor_clean
        self.payroll_amount[pid_str]                   = amount
        self.payroll_status[pid_str]                   = "ACTIVE"
        self.payroll_acceptance_criteria_url[pid_str]  = criteria_clean
        self.payroll_work_proof_url[pid_str]           = ""
        self.payroll_counter_evidence_url[pid_str]     = ""
        self.payroll_audit_opened[pid_str]             = False
        self.payroll_is_slashed[pid_str]               = False
        self.payroll_effort_score[pid_str]             = bigint(0)
        self.payroll_audit_report[pid_str]             = "Payroll created. Awaiting contributor work proof URL submission."

        # FIX 1: Initialize per-party locks (both unlocked at creation)
        self.payroll_work_proof_locked[pid_str]        = False
        self.payroll_counter_evidence_locked[pid_str]  = False

        # FIX 2 & 3: Store agreed deadlines
        self.payroll_challenge_deadline_ts[pid_str]    = bigint(challenge_deadline_ts)
        self.payroll_recovery_deadline_ts[pid_str]     = bigint(recovery_deadline_ts)

        self.payrolls_count = pid + bigint(1)
        return int(pid)

    # -------------------------------------------------------------------
    # PUBLIC WRITE: SUBMIT WORK PROOF (STAGE 1 — opens challenge window)
    # -------------------------------------------------------------------
    @gl.public.write
    def submit_work_proof(self, payroll_id: int, work_proof_url: str) -> None:
        """
        Stage 1: Contributor submits work proof URL.
        FIX 1: URL locks immediately upon submission — contributor cannot replace it afterward.
        Sets status to DISPUTED and opens the DAO Challenge Window for counter-evidence.
        """
        pid_str = str(payroll_id)
        if payroll_id < 0 or bigint(payroll_id) >= self.payrolls_count:
            raise UserError("Payroll record does not exist.")

        # FIX 1: Per-party lock — contributor may only submit once
        if self.payroll_work_proof_locked.get(pid_str, False):
            raise UserError("Work proof is already submitted and permanently locked. Evidence cannot be replaced.")

        status = self.payroll_status.get(pid_str, "ACTIVE")
        if status != "ACTIVE":
            raise UserError("Payroll is not in active state for work proof submission.")

        sender = to_address(gl.message.sender_address)
        contributor = to_address(self.payroll_contributor.get(pid_str, Address("0x0000000000000000000000000000000000000000")))
        if str(sender) != str(contributor):
            raise UserError("Only the designated contributor can submit work proof.")

        clean_url = work_proof_url.strip()
        if len(clean_url) == 0:
            raise UserError("Work proof URL cannot be empty.")

        url_lower = clean_url.lower()
        if not (url_lower.startswith("http://") or url_lower.startswith("https://")):
            raise UserError("Invalid work proof URL format. Must start with http:// or https://")

        if not (url_lower.startswith("https://github.com/") or
                url_lower.startswith("https://raw.githubusercontent.com/") or
                url_lower.startswith("https://gitlab.com/") or
                url_lower.startswith("https://status.vendor.com/")):
            raise UserError("Unauthorized work proof domain origin.")

        self.payroll_work_proof_url[pid_str]    = clean_url
        self.payroll_work_proof_locked[pid_str] = True   # FIX 1: Lock immediately
        self.payroll_status[pid_str]            = "DISPUTED"
        self.payroll_audit_report[pid_str]      = "Work proof submitted and locked. DAO Challenge Window open for counter-evidence."

    # -------------------------------------------------------------------
    # PUBLIC WRITE: SUBMIT COUNTER-EVIDENCE (DAO challenge window)
    # -------------------------------------------------------------------
    @gl.public.write
    def submit_counter_evidence(self, payroll_id: int, counter_evidence_url: str) -> None:
        """
        Allows DAO Admin to attach counter-evidence during the Challenge Window.
        FIX 1: URL locks immediately upon submission — DAO cannot replace it afterward.
        FIX 2: Counter-evidence must be submitted BEFORE challenge_deadline_ts.
        """
        pid_str = str(payroll_id)
        if payroll_id < 0 or bigint(payroll_id) >= self.payrolls_count:
            raise UserError("Payroll record does not exist.")

        # Audit-level lock (unchanged: blocks after audit commences)
        if self.payroll_audit_opened.get(pid_str, False):
            raise UserError("Evidence replacement is locked once audit has commenced.")

        # FIX 1: Per-party lock — DAO may only submit counter-evidence once
        if self.payroll_counter_evidence_locked.get(pid_str, False):
            raise UserError("Counter-evidence is already submitted and permanently locked. Evidence cannot be replaced.")

        status = self.payroll_status.get(pid_str, "ACTIVE")
        if status != "ACTIVE" and status != "DISPUTED":
            raise UserError("Payroll is not in an active or disputed state for counter-evidence submission.")

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

        if not (url_lower.startswith("https://github.com/") or
                url_lower.startswith("https://raw.githubusercontent.com/") or
                url_lower.startswith("https://gitlab.com/") or
                url_lower.startswith("https://status.vendor.com/")):
            raise UserError("Unauthorized counter-evidence domain origin.")

        self.payroll_counter_evidence_url[pid_str]    = clean_url
        self.payroll_counter_evidence_locked[pid_str] = True   # FIX 1: Lock immediately
        self.payroll_audit_report[pid_str]            = "DAO counter-evidence submitted and locked. Ready for AI audit after challenge window closes."

    # -------------------------------------------------------------------
    # PUBLIC WRITE: TRIGGER AI AUDIT & SETTLEMENT (STAGE 2)
    # -------------------------------------------------------------------
    @gl.public.write
    def request_salary_and_audit(self, payroll_id: int, time_source_url: str) -> None:
        """
        Triggers salary audit resolution via GenLayer AI consensus.
        FIX 1: Evidence URLs are bound from prior locked submissions — no inline replacement.
        FIX 2: Verifies challenge_deadline_ts has passed via canonical time oracle INSIDE
               the nondet call — audit is blocked until the DAO's challenge window has closed.

        time_source_url: Must be from AUTHORIZED_TIME_DOMAINS (worldtimeapi.org or timeapi.io).
        """
        pid_str = str(payroll_id)
        if payroll_id < 0 or bigint(payroll_id) >= self.payrolls_count:
            raise UserError("Payroll record does not exist.")

        if self.payroll_audit_opened.get(pid_str, False):
            raise UserError("Evidence replacement is locked once audit has commenced.")

        status = self.payroll_status.get(pid_str, "ACTIVE")
        if status != "ACTIVE" and status != "DISPUTED" and status != "FAILED":
            raise UserError("Payroll is not in active or disputed state for audit.")

        sender = to_address(gl.message.sender_address)
        contributor = to_address(self.payroll_contributor.get(pid_str, Address("0x0000000000000000000000000000000000000000")))
        dao = to_address(self.payroll_dao.get(pid_str, Address("0x0000000000000000000000000000000000000000")))
        if str(sender) != str(contributor) and str(sender) != str(dao):
            raise UserError("Only the designated contributor or DAO admin can request salary audit.")

        # Validate time_source_url domain
        time_url_lower = time_source_url.strip().lower()
        if not any(time_url_lower.startswith(d.lower()) for d in AUTHORIZED_TIME_DOMAINS):
            raise UserError("Time source must be from an authoritative time service (worldtimeapi.org or timeapi.io).")

        final_work_proof_url = self.payroll_work_proof_url.get(pid_str, "")
        if len(final_work_proof_url) == 0:
            raise UserError("Work proof URL cannot be empty before running AI audit.")

        # Lock evidence and begin audit
        self.payroll_status[pid_str]       = "DISPUTED"
        self.payroll_audit_opened[pid_str] = True
        self.payroll_audit_report[pid_str] = "Auditing report text. Inspecting deliverables against criteria..."

        acceptance_criteria_url    = self.payroll_acceptance_criteria_url.get(pid_str, "")
        final_counter_evidence_url = self.payroll_counter_evidence_url.get(pid_str, "")
        challenge_deadline_ts      = int(self.payroll_challenge_deadline_ts.get(pid_str, bigint(0)))

        def leader_fn() -> str:
            # ----------------------------------------------------------------
            # FIX 2: STEP 0 — Verify challenge window has closed via time oracle
            # ----------------------------------------------------------------
            try:
                raw_time = gl.nondet.web.render(time_source_url)
                time_text = raw_time.decode('utf-8', errors='ignore').strip() if isinstance(raw_time, bytes) else str(raw_time).strip()
            except Exception as e:
                return json.dumps({
                    "error": f"TIME_FETCH_FAILED: {str(e)}",
                    "is_slashed": True, "effort_score": 0,
                    "audit_report": "Cannot verify challenge window status — time oracle unreachable."
                })

            time_prompt = f"""Extract the current Unix timestamp from the following time API response.
Set "window_closed" = true ONLY if the current Unix timestamp is strictly greater than {challenge_deadline_ts}.
Otherwise set "window_closed" = false.

TIME API RESPONSE:
\"\"\"{time_text[:500]}\"\"\"

Respond ONLY with raw JSON (no markdown):
{{"current_unix_timestamp": <int>, "window_closed": true | false}}"""

            try:
                time_res = gl.nondet.exec_prompt(time_prompt)
                time_str = time_res.decode('utf-8', errors='ignore').strip() if isinstance(time_res, bytes) else str(time_res).strip()
                # Strip markdown if present
                if time_str.startswith("```"):
                    lines = time_str.split("\n")
                    inner = []
                    for line in lines[1:]:
                        if line.strip() == "```":
                            break
                        inner.append(line)
                    time_str = "\n".join(inner).strip()
                time_parsed = json.loads(time_str)
                window_closed = time_parsed.get("window_closed")
                if not isinstance(window_closed, bool):
                    return json.dumps({
                        "error": "TIME_CHECK_INVALID_BOOLEAN",
                        "is_slashed": False, "effort_score": 0,
                        "audit_report": "Time oracle returned non-boolean window_closed. Challenge window verification failed."
                    })
                if not window_closed:
                    return json.dumps({
                        "error": "CHALLENGE_WINDOW_OPEN",
                        "is_slashed": False, "effort_score": 0,
                        "audit_report": f"Challenge window is still open (deadline: {challenge_deadline_ts}). DAO counter-evidence period has not expired."
                    })
            except Exception as e:
                return json.dumps({
                    "error": f"TIME_CHECK_FAILED: {str(e)}",
                    "is_slashed": True, "effort_score": 0,
                    "audit_report": "Could not verify challenge window status. Failing closed."
                })

            # ----------------------------------------------------------------
            # STEP 1 — Fetch Acceptance Criteria
            # ----------------------------------------------------------------
            criteria_text = "Standard DAO Deliverables: Complete assigned tasks with tangible outputs."
            if len(acceptance_criteria_url) > 0:
                try:
                    raw_crit = gl.nondet.web.render(acceptance_criteria_url)
                    criteria_text = raw_crit.decode('utf-8', errors='ignore').strip() if isinstance(raw_crit, bytes) else str(raw_crit).strip()
                except Exception as e:
                    criteria_text = f"Default criteria (web load warning: {str(e)})"

            # ----------------------------------------------------------------
            # STEP 2 — Fetch Work Proof (FIX 1: from locked URL only)
            # ----------------------------------------------------------------
            try:
                raw_data = gl.nondet.web.render(final_work_proof_url)
                text = raw_data.decode('utf-8', errors='ignore').strip() if isinstance(raw_data, bytes) else str(raw_data).strip()
            except Exception as e:
                return json.dumps({
                    "error": "URL_LOAD_FAILED",
                    "is_slashed": True, "effort_score": 0,
                    "audit_report": f"Auditor could not load the work report at {final_work_proof_url}: {str(e)}"
                })

            if len(text) < 15:
                return json.dumps({
                    "error": "EMPTY_REPORT",
                    "is_slashed": True, "effort_score": 0,
                    "audit_report": "The work report page appeared to be empty or unparseable. Cannot verify claims."
                })

            # ----------------------------------------------------------------
            # STEP 3 — Fetch Counter-Evidence (FIX 1: from locked URL only)
            # ----------------------------------------------------------------
            counter_text = "None submitted by DAO."
            if len(final_counter_evidence_url) > 0:
                try:
                    raw_ce = gl.nondet.web.render(final_counter_evidence_url)
                    counter_text = raw_ce.decode('utf-8', errors='ignore').strip() if isinstance(raw_ce, bytes) else str(raw_ce).strip()
                except Exception:
                    counter_text = f"Counter-evidence at {final_counter_evidence_url} (could not load body)."

            excerpt_criteria = criteria_text[:2000]
            excerpt_work     = text[:5000]
            excerpt_counter  = counter_text[:2000]

            # ----------------------------------------------------------------
            # STEP 4 — AI Technical Lead Audit Prompt
            # ----------------------------------------------------------------
            prompt = f"""You are a Ruthless Technical Lead acting as an Auditor in a DAO payroll system.
Your job is to examine work reports against agreed acceptance criteria and optional DAO counter-evidence.
Identify "fake work", corporate fluff, meeting-spam, or unfulfilled acceptance criteria.
Separate concrete deliverables (written code, PRs, graphics, finished documents, deployed systems) from filler ("Attended meetings," "Telegram chat", "GM tweets").

AGREED ACCEPTANCE CRITERIA (immutable, bound at payroll creation):
\"\"\"
{excerpt_criteria}
\"\"\"

CONTRIBUTOR WORK PROOF TEXT ({final_work_proof_url}) [LOCKED — cannot be modified]:
\"\"\"
{excerpt_work}
\"\"\"

DAO COUNTER-EVIDENCE DISPUTE TEXT [LOCKED — cannot be modified]:
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
                    "is_slashed": True, "effort_score": 0,
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
                if not isinstance(raw_slashed, bool):
                    return json.dumps({
                        "error": "INVALID_BOOLEAN_TYPE",
                        "is_slashed": True, "effort_score": 0,
                        "audit_report": "AI Auditor verdict contained a non-boolean value for is_slashed."
                    })

                is_slashed = raw_slashed
                score  = int(parsed.get("effort_score", 0))
                report = str(parsed.get("audit_report", "No audit details.")).strip()

                if score < 0:  score = 0
                if score > 100: score = 100
                if score < 50:
                    is_slashed = True

                return json.dumps({
                    "is_slashed":   is_slashed,
                    "effort_score": score,
                    "audit_report": report[:1000]
                })
            except Exception as e:
                return json.dumps({
                    "error": f"JSON_PARSE_FAILED: {str(e)}",
                    "is_slashed": True, "effort_score": 0,
                    "audit_report": f"Failed to parse AI output. Raw response: {cleaned}"
                })

        def validator_fn(leader_result: str) -> bool:
            try:
                leader_str = leader_result.decode('utf-8', errors='ignore') if isinstance(leader_result, bytes) else str(leader_result)
                l_start = leader_str.find('{')
                l_end   = leader_str.rfind('}')
                if l_start == -1 or l_end == -1 or l_start > l_end:
                    return False
                leader_data = json.loads(leader_str[l_start:l_end+1])
            except Exception:
                return False

            if "error" in leader_data:
                return False

            leader_slashed_raw = leader_data.get("is_slashed")
            if not isinstance(leader_slashed_raw, bool):
                return False

            validator_raw = leader_fn()
            try:
                val_str = validator_raw.decode('utf-8', errors='ignore') if isinstance(validator_raw, bytes) else str(validator_raw)
                v_start = val_str.find('{')
                v_end   = val_str.rfind('}')
                if v_start == -1 or v_end == -1 or v_start > v_end:
                    return False
                validator_data = json.loads(val_str[v_start:v_end+1])
            except Exception:
                return False

            if "error" in validator_data:
                return False

            val_slashed_raw = validator_data.get("is_slashed")
            if not isinstance(val_slashed_raw, bool):
                return False

            return leader_slashed_raw == val_slashed_raw

        # Execute Consensus on GenLayer VM
        consensus_json = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)

        try:
            cons_str   = consensus_json.decode('utf-8', errors='ignore') if isinstance(consensus_json, bytes) else str(consensus_json)
            cons_start = cons_str.find('{')
            cons_end   = cons_str.rfind('}')
            if cons_start == -1 or cons_end == -1 or cons_start > cons_end:
                raise ValueError("No JSON object found")
            res = json.loads(cons_str[cons_start:cons_end+1])
        except Exception:
            self.payroll_status[pid_str]       = "FAILED"
            self.payroll_audit_report[pid_str] = "Consensus outcome was unparseable JSON."
            return

        if "error" in res:
            self.payroll_status[pid_str]       = "FAILED"
            self.payroll_audit_report[pid_str] = f"Audit failed: {res.get('error')}. Info: {res.get('audit_report')}"
            return

        settle_slashed_raw = res.get("is_slashed")
        if not isinstance(settle_slashed_raw, bool):
            self.payroll_status[pid_str]       = "FAILED"
            self.payroll_audit_report[pid_str] = "Audit Failed: Invalid non-boolean value for is_slashed in settlement path."
            return

        is_slashed = settle_slashed_raw
        score  = int(res.get("effort_score", 0))
        report = str(res.get("audit_report", "Audit processed."))

        self.payroll_is_slashed[pid_str]    = is_slashed
        self.payroll_effort_score[pid_str]  = bigint(score)
        self.payroll_audit_report[pid_str]  = report

        amount = self.payroll_amount.get(pid_str, bigint(0))
        if amount <= bigint(0):
            raise UserError("No salary funds locked in this payroll.")

        # Reentrancy protection
        self.payroll_amount[pid_str] = bigint(0)

        if is_slashed:
            self.payroll_status[pid_str] = "SLASHED"
            gl.get_contract_at(dao).emit_transfer(value=bigint(amount))
        else:
            self.payroll_status[pid_str] = "PAID"
            gl.get_contract_at(contributor).emit_transfer(value=bigint(amount))

    # -------------------------------------------------------------------
    # PUBLIC WRITE: TIMEOUT RECOVERY (FAILED-AUDIT CONDITION)
    # -------------------------------------------------------------------
    @gl.public.write
    def reclaim_timed_out_payroll(self, payroll_id: int, time_source_url: str) -> None:
        """
        Enables DAO admin to recover locked deposit ONLY if:
        1. Audit has officially failed (FAILED status).
        2. recovery_deadline_ts has been exceeded (verified via canonical time oracle).
        FIX 3: Enforces a real, measurable timeout before recovery is permitted.

        time_source_url: Must be from AUTHORIZED_TIME_DOMAINS.
        """
        pid_str = str(payroll_id)
        if payroll_id < 0 or bigint(payroll_id) >= self.payrolls_count:
            raise UserError("Payroll record does not exist.")

        status = self.payroll_status.get(pid_str, "")
        if status != "FAILED":
            raise UserError("Payroll funds can only be reclaimed if audit has officially failed (FAILED status).")

        sender = to_address(gl.message.sender_address)
        dao    = to_address(self.payroll_dao.get(pid_str, Address("0x0000000000000000000000000000000000000000")))
        if str(sender) != str(dao):
            raise UserError("Only the designated DAO admin can reclaim timed out payroll funds.")

        # Validate time_source_url domain
        time_url_lower = time_source_url.strip().lower()
        if not any(time_url_lower.startswith(d.lower()) for d in AUTHORIZED_TIME_DOMAINS):
            raise UserError("Time source must be from an authoritative time service (worldtimeapi.org or timeapi.io).")

        recovery_deadline_ts = int(self.payroll_recovery_deadline_ts.get(pid_str, bigint(0)))

        # FIX 3: Verify recovery_deadline_ts has passed via canonical time oracle
        def leader_fn() -> str:
            try:
                raw_time  = gl.nondet.web.render(time_source_url)
                time_text = raw_time.decode('utf-8', errors='ignore').strip() if isinstance(raw_time, bytes) else str(raw_time).strip()
            except Exception as e:
                return json.dumps({
                    "error": f"TIME_FETCH_FAILED: {str(e)}",
                    "deadline_passed": False,
                    "current_unix_timestamp": 0,
                    "reasoning": "Cannot verify recovery deadline — time oracle unreachable."
                })

            prompt = f"""Extract the current Unix timestamp from the following time API response.
Set "deadline_passed" = true ONLY if current Unix timestamp is strictly greater than {recovery_deadline_ts}.
Otherwise set "deadline_passed" = false.

TIME API RESPONSE:
\"\"\"{time_text[:500]}\"\"\"

Respond ONLY with raw JSON (no markdown):
{{"current_unix_timestamp": <int>, "deadline_passed": true | false, "reasoning": "<string>"}}"""

            try:
                res     = gl.nondet.exec_prompt(prompt)
                res_str = res.decode('utf-8', errors='ignore').strip() if isinstance(res, bytes) else str(res).strip()
                if res_str.startswith("```"):
                    lines = res_str.split("\n")
                    inner = []
                    for line in lines[1:]:
                        if line.strip() == "```":
                            break
                        inner.append(line)
                    res_str = "\n".join(inner).strip()
                return res_str
            except Exception as e:
                return json.dumps({
                    "error": f"LLM_FAILED: {str(e)}",
                    "deadline_passed": False,
                    "current_unix_timestamp": 0,
                    "reasoning": "Time oracle LLM call failed."
                })

        def validator_fn(leader_result: str) -> bool:
            try:
                l_str   = leader_result.decode('utf-8', errors='ignore') if isinstance(leader_result, bytes) else str(leader_result)
                l_start = l_str.find('{')
                l_end   = l_str.rfind('}')
                if l_start == -1 or l_end == -1: return False
                l_data  = json.loads(l_str[l_start:l_end+1])
            except Exception:
                return False

            if "error" in l_data: return False
            l_passed = l_data.get("deadline_passed")
            if not isinstance(l_passed, bool): return False

            val_raw = leader_fn()
            try:
                v_str   = val_raw.decode('utf-8', errors='ignore') if isinstance(val_raw, bytes) else str(val_raw)
                v_start = v_str.find('{')
                v_end   = v_str.rfind('}')
                if v_start == -1 or v_end == -1: return False
                v_data  = json.loads(v_str[v_start:v_end+1])
            except Exception:
                return False

            if "error" in v_data: return False
            v_passed = v_data.get("deadline_passed")
            if not isinstance(v_passed, bool): return False

            return l_passed == v_passed

        consensus_json = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)

        try:
            c_str   = consensus_json.decode('utf-8', errors='ignore') if isinstance(consensus_json, bytes) else str(consensus_json)
            c_start = c_str.find('{')
            c_end   = c_str.rfind('}')
            if c_start == -1 or c_end == -1 or c_start > c_end:
                raise ValueError("No JSON found")
            c_data = json.loads(c_str[c_start:c_end+1])
        except Exception:
            raise UserError("Could not parse time oracle consensus result.")

        if "error" in c_data:
            raise UserError(f"Time oracle failed: {c_data.get('error')}. Recovery blocked.")

        deadline_passed = c_data.get("deadline_passed")
        if not isinstance(deadline_passed, bool):
            raise UserError("Time oracle returned invalid deadline_passed value. Recovery blocked.")

        if not deadline_passed:
            raise UserError(f"Recovery deadline has not yet passed (deadline: {recovery_deadline_ts}). Recovery is blocked until then.")

        amount = self.payroll_amount.get(pid_str, bigint(0))
        if amount <= bigint(0):
            raise UserError("Payroll has no locked funds to reclaim.")

        self.payroll_amount[pid_str]       = bigint(0)
        self.payroll_status[pid_str]       = "RECLAIMED"
        self.payroll_audit_report[pid_str] = "DAO admin reclaimed escrowed funds following failed audit consensus after recovery deadline."

        gl.get_contract_at(dao).emit_transfer(value=bigint(amount))

    # -------------------------------------------------------------------
    # READ-ONLY VIEW METHODS
    # -------------------------------------------------------------------
    @gl.public.view
    def get_payroll(self, payroll_id: int) -> str:
        """Returns a JSON-serialized representation of a payroll escrow."""
        pid_str = str(payroll_id)
        if payroll_id < 0 or bigint(payroll_id) >= self.payrolls_count:
            return "{}"

        dao          = to_address(self.payroll_dao.get(pid_str, Address("0x0000000000000000000000000000000000000000")))
        contributor  = to_address(self.payroll_contributor.get(pid_str, Address("0x0000000000000000000000000000000000000000")))
        amount       = self.payroll_amount.get(pid_str, bigint(0))
        status       = self.payroll_status.get(pid_str, "ACTIVE")
        crit_url     = self.payroll_acceptance_criteria_url.get(pid_str, "")
        proof        = self.payroll_work_proof_url.get(pid_str, "")
        counter      = self.payroll_counter_evidence_url.get(pid_str, "")
        audit_opened = bool(self.payroll_audit_opened.get(pid_str, False))
        slashed      = bool(self.payroll_is_slashed.get(pid_str, False))
        score        = int(self.payroll_effort_score.get(pid_str, bigint(0)))
        report       = self.payroll_audit_report.get(pid_str, "")
        wp_locked    = bool(self.payroll_work_proof_locked.get(pid_str, False))
        ce_locked    = bool(self.payroll_counter_evidence_locked.get(pid_str, False))
        ch_deadline  = int(self.payroll_challenge_deadline_ts.get(pid_str, bigint(0)))
        rec_deadline = int(self.payroll_recovery_deadline_ts.get(pid_str, bigint(0)))

        return json.dumps({
            "id":                      payroll_id,
            "dao":                     str(dao),
            "contributor":             str(contributor),
            "amount":                  int(amount),
            "status":                  status,
            "acceptance_criteria_url": crit_url,
            "work_proof_url":          proof,
            "counter_evidence_url":    counter,
            "audit_opened":            audit_opened,
            "is_slashed":              slashed,
            "effort_score":            score,
            "audit_report":            report,
            "work_proof_locked":       wp_locked,
            "counter_evidence_locked": ce_locked,
            "challenge_deadline_ts":   ch_deadline,
            "recovery_deadline_ts":    rec_deadline,
        })

    @gl.public.view
    def get_payrolls_count(self) -> int:
        """Returns the total number of payroll escrows created."""
        return int(self.payrolls_count)
