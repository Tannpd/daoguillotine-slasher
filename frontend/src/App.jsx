import React, { useState, useEffect } from 'react';
import { 
  useDAOGuillotine, 
  formatGen 
} from './useDAOGuillotine';
import { 
  ShieldAlert, 
  Terminal, 
  User, 
  Link, 
  Lock, 
  Slash, 
  FileText, 
  Skull, 
  Briefcase,
  AlertOctagon,
  Scale
} from 'lucide-react';

export default function App() {
  const {
    address,
    glAccount,
    payrolls,
    contractBalance,
    loading,
    error,
    txHash,
    txStatus,
    connectWallet,
    fetchPayrollsState,
    createPayroll,
    requestSalary,
    contractAddress
  } = useDAOGuillotine();

  const [activeTab, setActiveTab] = useState('CREATE_PAYROLL'); // CREATE_PAYROLL or CABINET
  const [selectedPayrollId, setSelectedPayrollId] = useState(null);
  
  // Form inputs
  const [contributorInput, setContributorInput] = useState('');
  const [amountInput, setAmountInput] = useState('5.0');
  const [workProofUrlInput, setWorkProofUrlInput] = useState('');

  // Slashed animation trigger states
  const [triggerSlashAnim, setTriggerSlashAnim] = useState(false);

  const selectedPayroll = payrolls.find(p => Number(p.id) === Number(selectedPayrollId));

  // Auto select first payroll
  useEffect(() => {
    if (activeTab === 'CABINET' && payrolls.length > 0 && selectedPayrollId === null) {
      setSelectedPayrollId(payrolls[0].id);
    }
  }, [activeTab, payrolls, selectedPayrollId]);

  // Watch for audit changes to trigger animation
  useEffect(() => {
    if (selectedPayroll) {
      if (selectedPayroll.status === 'SLASHED') {
        setTriggerSlashAnim(true);
        const timer = setTimeout(() => {
          setTriggerSlashAnim(false);
        }, 1000);
        return () => clearTimeout(timer);
      } else {
        setTriggerSlashAnim(false);
      }
    }
  }, [selectedPayrollId, selectedPayroll?.status]);

  const handleCreatePayroll = async (e) => {
    e.preventDefault();
    if (!contributorInput || !amountInput) return;
    try {
      await createPayroll(contributorInput, amountInput);
      setContributorInput('');
      setAmountInput('5.0');
      setActiveTab('CABINET');
      setSelectedPayrollId(0); // View newest
    } catch (err) {
      console.error(err);
    }
  };

  const handleRequestSalary = async (e) => {
    e.preventDefault();
    if (!workProofUrlInput || selectedPayrollId === null) return;
    try {
      await requestSalary(selectedPayrollId, workProofUrlInput);
      setWorkProofUrlInput('');
    } catch (err) {
      console.error(err);
    }
  };

  // Render value extraction meter segments
  const renderMeter = (score, isSlashed) => {
    const totalSegments = 20;
    const filledSegments = Math.round((Number(score) / 100) * totalSegments);
    const segments = [];
    for (let i = 0; i < totalSegments; i++) {
      const isFilled = i < filledSegments;
      let segmentClass = '';
      if (isFilled) {
        segmentClass = isSlashed ? 'filled-low' : 'filled-high';
      }
      segments.push(
        <div key={i} className={`meter-segment ${segmentClass}`} />
      );
    }
    return segments;
  };

  return (
    <div className={`terminal-container ${triggerSlashAnim ? 'slash-screen-shake slash-screen-flash' : ''}`}>
      {/* Loading overlay */}
      {loading && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0, 0, 0, 0.95)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', zIndex: 200, border: '4px solid var(--blood-red)' }}>
          <Skull size={80} color="var(--blood-red)" style={{ animation: 'pulse-badge 1s infinite alternate' }} />
          <h2 style={{ fontFamily: 'var(--font-title)', fontSize: '32px', color: '#fff', marginTop: '24px', letterSpacing: '2px' }}>
            [ EXECUTION IN PROGRESS ]
          </h2>
          <p style={{ color: 'var(--steel-light)', marginTop: '12px', fontSize: '13px', maxWidth: '600px', textAlign: 'center', fontFamily: 'var(--font-mono)', padding: '0 20px' }}>
            {txStatus || 'Writing instructions to the GenLayer virtual machine...'}
          </p>
          {txHash && (
            <div style={{ marginTop: '20px', fontSize: '11px', color: 'var(--corp-blue)', fontFamily: 'var(--font-mono)' }}>
              TX_HASH: {txHash}
            </div>
          )}
        </div>
      )}

      {/* caution banners */}
      <div className="caution-banner" />

      <div className="terminal-frame">
        {/* Header */}
        <header className="terminal-header">
          <div>
            <div className="terminal-title">
              <Skull size={36} color="var(--blood-red)" />
              <span>DAO GUILLOTINE</span>
            </div>
            <div style={{ color: 'var(--steel-light)', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '1.5px', marginTop: '4px' }}>
              Contributor Slasher // Fluff Audit Protocol v0.2.16
            </div>
          </div>

          <div>
            {address ? (
              <div style={{ background: '#111', border: '2px solid var(--steel-gray)', padding: '8px 16px', color: 'var(--corp-blue)', fontSize: '12px' }}>
                LOGGED_AS // {address.slice(0, 8)}...{address.slice(-8)}
              </div>
            ) : (
              <button onClick={connectWallet} className="terminal-btn" style={{ borderColor: 'var(--corp-blue)', color: 'var(--corp-blue)' }}>
                INITIATE INTERACTION
              </button>
            )}
          </div>
        </header>

        {/* Auth prompt */}
        {!address ? (
          <div style={{ textAlign: 'center', padding: '80px 20px', background: '#090909' }}>
            <ShieldAlert size={60} color="var(--blood-red)" style={{ margin: '0 auto 20px auto' }} />
            <h2 style={{ fontFamily: 'var(--font-title)', fontSize: '32px', color: '#fff', marginBottom: '12px', letterSpacing: '1px' }}>
              AUTHENTICATION REQUISITE
            </h2>
            <p style={{ color: 'var(--steel-light)', maxWidth: '500px', margin: '0 auto 30px auto', fontSize: '13px', lineHeight: '20px' }}>
              Load MetaMask or your GenLayer Studio browser environment to audit developer work metrics and release bounty assets.
            </p>
            <button onClick={connectWallet} className="terminal-btn">
              CONNECT ACCESS KEY
            </button>
          </div>
        ) : (
          <div>
            {/* Tabs */}
            <div className="terminal-tabs">
              <button 
                onClick={() => setActiveTab('CREATE_PAYROLL')}
                className={`terminal-tab ${activeTab === 'CREATE_PAYROLL' ? 'active' : ''}`}
              >
                [+] ESCROW BOUNTY
              </button>
              <button 
                onClick={() => {
                  setActiveTab('CABINET');
                  fetchPayrollsState();
                }}
                className={`terminal-tab ${activeTab === 'CABINET' ? 'active' : ''}`}
              >
                📁 CASE REPOSITORY ({payrolls.length})
              </button>
            </div>

            {/* Contract status info */}
            <div className="terminal-meta-bar">
              <div>ACTIVE CONTRACT BALANCE: {formatGen(contractBalance)} GEN</div>
              <div>STUDIONET ADDR: {contractAddress || 'No Address'}</div>
            </div>

            <div style={{ padding: '30px' }}>
              {error && (
                <div style={{ background: 'rgba(255, 0, 60, 0.08)', border: '2px solid var(--blood-red)', padding: '16px', color: '#ffa3b1', fontSize: '12px', marginBottom: '24px' }}>
                  <span style={{ fontWeight: 'bold' }}>SYSTEM ERROR //</span> {error}
                </div>
              )}

              {/* TAB CONTENT: CREATE_PAYROLL */}
              {activeTab === 'CREATE_PAYROLL' && (
                <div style={{ maxWidth: '700px', margin: '0 auto' }}>
                  <div className="module-panel">
                    <h3 className="module-title">
                      <Lock size={18} color="var(--corp-blue)" />
                      LOCK CONTRIBUTOR BOUNTY
                    </h3>
                    <p style={{ color: 'var(--steel-light)', fontSize: '12px', marginBottom: '24px', lineHeight: '18px' }}>
                      Locks payment assets in escrow for a designated developer address. Funds are held until audited.
                    </p>

                    <form onSubmit={handleCreatePayroll}>
                      <div className="terminal-input-group">
                        <label className="terminal-label">CONTRIBUTOR ADDRESS</label>
                        <input 
                          type="text" 
                          placeholder="0x90F8bf651d130c507982e1cfd84d12A9c0fFd2Ef" 
                          value={contributorInput}
                          onChange={(e) => setContributorInput(e.target.value)}
                          className="terminal-input"
                          required
                        />
                      </div>

                      <div className="terminal-input-group">
                        <label className="terminal-label">PAYROLL VALUE (GEN)</label>
                        <input 
                          type="number" 
                          step="0.001" 
                          min="0.001"
                          placeholder="5.0" 
                          value={amountInput}
                          onChange={(e) => setAmountInput(e.target.value)}
                          className="terminal-input"
                          required
                        />
                      </div>

                      <div style={{ textAlign: 'right', marginTop: '30px' }}>
                        <button type="submit" className="terminal-btn">
                          ESCROW BOUNTY LOCK
                        </button>
                      </div>
                    </form>
                  </div>
                </div>
              )}

              {/* TAB CONTENT: CABINET */}
              {activeTab === 'CABINET' && (
                <div style={{ display: 'grid', gridTemplateColumns: payrolls.length > 0 ? '320px 1fr' : '1fr', gap: '30px' }}>
                  
                  {/* CABINET SIDEBAR */}
                  {payrolls.length > 0 ? (
                    <div className="cabinet-sidebar">
                      <h4 style={{ fontFamily: 'var(--font-title)', fontSize: '18px', color: 'var(--steel-light)', borderBottom: '2px solid var(--steel-gray)', paddingBottom: '10px', marginBottom: '16px' }}>
                        FILES
                      </h4>
                      <div style={{ maxHeight: '600px', overflowY: 'auto' }}>
                        {payrolls.map((payroll) => {
                          const isSlashed = payroll.status === 'SLASHED';
                          const isPaid = payroll.status === 'PAID';
                          
                          let statusClass = 'badge-active';
                          if (isSlashed) statusClass = 'badge-slashed';
                          if (isPaid) statusClass = 'badge-paid';

                          return (
                            <div 
                              key={payroll.id}
                              className={`cabinet-card ${Number(selectedPayrollId) === Number(payroll.id) ? 'selected' : ''}`}
                              onClick={() => setSelectedPayrollId(payroll.id)}
                            >
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                                <span style={{ fontFamily: 'var(--font-title)', fontSize: '18px' }}>
                                  CASE #{payroll.id}
                                </span>
                                <span className={`badge-status ${statusClass}`}>
                                  {payroll.status}
                                </span>
                              </div>
                              <div style={{ fontSize: '11px', color: 'var(--steel-light)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                DEV: {payroll.contributor.slice(0, 14)}...
                              </div>
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '10px' }}>
                                <span style={{ fontSize: '12px', color: 'var(--corp-blue)', fontWeight: 'bold' }}>
                                  {formatGen(payroll.amount)} GEN
                                </span>
                                {payroll.effort_score > 0 && (
                                  <span style={{ fontSize: '10px', color: 'var(--steel-light)' }}>
                                    EFFORT: {payroll.effort_score}%
                                  </span>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  ) : (
                    <div style={{ textAlign: 'center', padding: '60px 0', border: '2px dashed var(--steel-gray)' }}>
                      <Briefcase size={40} color="var(--steel-light)" style={{ margin: '0 auto 16px auto' }} />
                      <p style={{ color: 'var(--steel-light)' }}>NO SALARY RECORDS ACTIVE</p>
                    </div>
                  )}

                  {/* ACTIVE CRT VIEW */}
                  {selectedPayroll && (
                    <div className="module-panel" style={{ padding: '0px', background: 'transparent', border: 'none' }}>
                      <div className="crt-screen crt-console">
                        
                        {/* Audit Stamp overlay */}
                        {selectedPayroll.status === 'SLASHED' && (
                          <div className="stamp-slashed-banner">
                            [ EFFORT REJECTED - FUNDS SLASHED ]
                          </div>
                        )}
                        {selectedPayroll.status === 'PAID' && (
                          <div className="stamp-paid-banner">
                            [ COMPLIANT - SALARY DISBURSED ]
                          </div>
                        )}

                        <h3 className="module-title" style={{ color: '#fff', borderColor: 'var(--steel-gray)' }}>
                          PAYROLL DOSSIER DETAILS
                        </h3>

                        <div className="crt-status-row">
                          <div className="crt-label-cell">CASE REF:</div>
                          <div>#000{selectedPayroll.id}</div>
                        </div>

                        <div className="crt-status-row">
                          <div className="crt-label-cell">DAO SOURCE:</div>
                          <div style={{ fontSize: '12px' }}>{selectedPayroll.dao}</div>
                        </div>

                        <div className="crt-status-row">
                          <div className="crt-label-cell">CONTRIBUTOR:</div>
                          <div style={{ fontSize: '12px' }}>{selectedPayroll.contributor}</div>
                        </div>

                        <div className="crt-status-row">
                          <div className="crt-label-cell">ESCROW SUM:</div>
                          <div style={{ fontSize: '16px', color: 'var(--corp-blue)', fontWeight: 'bold' }}>
                            {formatGen(selectedPayroll.amount)} GEN
                          </div>
                        </div>

                        {/* Effort meter */}
                        {selectedPayroll.effort_score > 0 && (
                          <div className="meter-container">
                            <div className="meter-label">
                              <span>PRODUCTIVITY GAUGED VALUE</span>
                              <span>{selectedPayroll.effort_score}% EFFORT SCORE</span>
                            </div>
                            <div className="meter-track">
                              {renderMeter(selectedPayroll.effort_score, selectedPayroll.is_slashed)}
                            </div>
                          </div>
                        )}

                        {/* Audit report display */}
                        {selectedPayroll.audit_report && (
                          <div style={{ background: '#111', border: '1px solid var(--steel-gray)', padding: '16px', marginTop: '20px' }}>
                            <div style={{ color: 'var(--blood-red)', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                              <Terminal size={12} /> SYSTEM LOG: AUDITOR DECREE
                            </div>
                            <div style={{ fontStyle: 'italic', fontSize: '13px', lineHeight: '20px' }}>
                              "{selectedPayroll.audit_report}"
                            </div>
                            {selectedPayroll.work_proof_url && (
                              <div style={{ marginTop: '12px', fontSize: '11px', borderTop: '1px dashed var(--steel-gray)', paddingTop: '8px' }}>
                                <span style={{ color: 'var(--steel-light)' }}>SUBMITTED EVIDENCE: </span>
                                <a 
                                  href={selectedPayroll.work_proof_url} 
                                  target="_blank" 
                                  rel="noreferrer" 
                                  style={{ color: 'var(--corp-blue)', textDecoration: 'underline' }}
                                >
                                  {selectedPayroll.work_proof_url}
                                </a>
                              </div>
                            )}
                          </div>
                        )}

                        {/* Action buttons */}
                        <div style={{ marginTop: '30px', borderTop: '2px dashed var(--steel-gray)', paddingTop: '20px' }}>
                          {selectedPayroll.status === 'ACTIVE' ? (
                            <div>
                              {(address.toLowerCase() === selectedPayroll.contributor.toLowerCase() || address.toLowerCase() === selectedPayroll.dao.toLowerCase()) ? (
                                <div>
                                  <div style={{ background: 'rgba(0, 229, 255, 0.05)', border: '1px solid var(--corp-blue-dim)', padding: '12px', borderRadius: '4px', fontSize: '11px', color: '#a5f3fc', marginBottom: '16px' }}>
                                    ROLE RECOGNIZED // {address.toLowerCase() === selectedPayroll.contributor.toLowerCase() ? "Contributor" : "DAO Admin"}. Submit work proof URL below to trigger auditing.
                                  </div>

                                  {/* QUICK TEST FILL BUTTONS */}
                                  <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
                                    <button
                                      type="button"
                                      style={{
                                        background: 'rgba(0, 229, 255, 0.15)',
                                        border: '1px solid rgba(0, 229, 255, 0.4)',
                                        color: '#a5f3fc',
                                        fontSize: '11px',
                                        padding: '4px 8px',
                                        borderRadius: '4px',
                                        cursor: 'pointer',
                                        fontFamily: 'monospace'
                                      }}
                                      onClick={() => setWorkProofUrlInput('https://daoguillotine-slasher.vercel.app/mock_report_solid_work.txt')}
                                    >
                                      + Fill Solid Work Report (Payout)
                                    </button>

                                    <button
                                      type="button"
                                      style={{
                                        background: 'rgba(239, 68, 68, 0.15)',
                                        border: '1px solid rgba(239, 68, 68, 0.4)',
                                        color: '#fca5a5',
                                        fontSize: '11px',
                                        padding: '4px 8px',
                                        borderRadius: '4px',
                                        cursor: 'pointer',
                                        fontFamily: 'monospace'
                                      }}
                                      onClick={() => setWorkProofUrlInput('https://daoguillotine-slasher.vercel.app/mock_report_fluff_meetings.txt')}
                                    >
                                      + Fill Fluff Meetings Report (Slash & Refund DAO)
                                    </button>
                                  </div>

                                  <form onSubmit={handleRequestSalary} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                                    <div className="terminal-input-group" style={{ marginBottom: '10px' }}>
                                      <label className="terminal-label" style={{ fontSize: '12px' }}>WORK PROOF URL (GitHub Gist, Notion Doc, Blog Post)</label>
                                      <input 
                                        type="text" 
                                        placeholder="https://daoguillotine-slasher.vercel.app/mock_report_solid_work.txt" 
                                        value={workProofUrlInput || 'https://daoguillotine-slasher.vercel.app/mock_report_solid_work.txt'}
                                        onChange={(e) => setWorkProofUrlInput(e.target.value)}
                                        className="terminal-input"
                                        required
                                      />
                                    </div>
                                    <div style={{ textAlign: 'right' }}>
                                      <button type="submit" className="terminal-btn terminal-btn-slash" style={{ width: '100%' }} disabled={loading}>
                                        {loading ? 'AUDITING...' : 'TRIGGER AUDIT & CLAIM PAYOUT'}
                                      </button>
                                    </div>
                                  </form>
                                </div>
                              ) : (
                                <div style={{ color: 'var(--steel-light)', fontSize: '12px', textAlign: 'center', padding: '16px', background: '#090909', border: '1px solid var(--steel-gray)' }}>
                                  Awaiting contributor or DAO claim. Connected wallet is not a recognized party for this payroll.
                                </div>
                              )}
                            </div>
                          ) : (
                            <div style={{ background: 'rgba(255,255,255,0.02)', padding: '16px', border: '1px solid var(--steel-gray)', color: 'var(--steel-light)', textAlign: 'center', fontSize: '12px' }}>
                              Dossier Locked. Final state achieved. Payout settled or confiscated.
                            </div>
                          )}
                        </div>

                      </div>
                    </div>
                  )}

                </div>
              )}

            </div>
          </div>
        )}

        {/* Footer monitor */}
        <footer style={{ background: '#080808', borderTop: '4px solid var(--steel-gray)', padding: '20px 30px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '30px', alignItems: 'center' }}>
            <div>
              <div style={{ fontFamily: 'var(--font-title)', fontSize: '16px', color: '#fff', marginBottom: '8px' }}>
                HR AUDIT SUB-PROCESSOR
              </div>
              <p style={{ fontSize: '11px', color: 'var(--steel-light)', lineHeight: '16px' }}>
                Guillotine scans contribution logs in distributed nodes. Validates core slashing outcomes via consensus. Fluff score below 50% triggers total refund to the DAO treasury.
              </p>
            </div>

            <div>
              <div className="crt-monitor-log">
                <div className="crt-log-line">&gt; Initiating DAOGuillotine security framework... [ACTIVE]</div>
                <div className="crt-log-line">&gt; Listening on GenLayer StudioNet contract listener.</div>
                {txStatus && <div className="crt-log-line" style={{ color: 'var(--corp-blue)' }}>&gt; [SYSTEM STATUS] {txStatus}</div>}
                {txHash && <div className="crt-log-line">&gt; [TX TRANSMITTED] {txHash}</div>}
                <div className="crt-log-line">&gt; Execution pool online. Awaiting task inputs.</div>
              </div>
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
}
