import React, { useState, useEffect } from 'react';
import { 
  useDAOGuillotine, 
  formatGen 
} from './useDAOGuillotine';
import { 
  ShieldCheck, 
  Wallet, 
  PlusCircle, 
  FolderOpen, 
  Lock, 
  CheckCircle2, 
  AlertCircle, 
  ExternalLink,
  Coins,
  Scale,
  Sparkles,
  RefreshCw,
  Zap,
  Globe,
  Cpu,
  ArrowRight,
  Shield,
  Check,
  Terminal,
  FileCode,
  FileCheck
} from 'lucide-react';

export default function App() {
  const {
    address,
    payrolls,
    contractBalance,
    loading,
    error,
    txHash,
    txStatus,
    connectWallet,
    fetchPayrollsState,
    createPayroll,
    submitWorkProof,
    submitCounterEvidence,
    reclaimTimedOutPayroll,
    requestSalary,
    contractAddress
  } = useDAOGuillotine();

  const [activeTab, setActiveTab] = useState('LANDING'); // LANDING, CREATE_PAYROLL, CABINET
  const [selectedPayrollId, setSelectedPayrollId] = useState(null);
  
  // Form inputs
  const [contributorInput, setContributorInput] = useState('');
  const [amountInput, setAmountInput] = useState('5.0');
  const [acceptanceCriteriaUrlInput, setAcceptanceCriteriaUrlInput] = useState('');
  const [workProofUrlInput, setWorkProofUrlInput] = useState('');
  const [counterEvidenceUrlInput, setCounterEvidenceUrlInput] = useState('');

  const selectedPayroll = payrolls.find(p => Number(p.id) === Number(selectedPayrollId));

  // Auto select first payroll when entering cabinet
  useEffect(() => {
    if (activeTab === 'CABINET' && payrolls.length > 0 && selectedPayrollId === null) {
      setSelectedPayrollId(payrolls[0].id);
    }
  }, [activeTab, payrolls, selectedPayrollId]);

  const handleCreatePayroll = async (e) => {
    e.preventDefault();
    if (!contributorInput || !amountInput || !acceptanceCriteriaUrlInput) return;
    try {
      await createPayroll(contributorInput, amountInput, acceptanceCriteriaUrlInput);
      setContributorInput('');
      setAmountInput('5.0');
      setAcceptanceCriteriaUrlInput('');
      setActiveTab('CABINET');
      setSelectedPayrollId(0);
    } catch (err) {
      console.error(err);
    }
  };

  const handleSubmitWorkProof = async (e) => {
    e.preventDefault();
    if (!workProofUrlInput || selectedPayrollId === null) return;
    try {
      await submitWorkProof(selectedPayrollId, workProofUrlInput);
      setWorkProofUrlInput('');
    } catch (err) {
      console.error(err);
    }
  };

  const handleSubmitCounterEvidence = async (e) => {
    e.preventDefault();
    if (!counterEvidenceUrlInput || selectedPayrollId === null) return;
    try {
      await submitCounterEvidence(selectedPayrollId, counterEvidenceUrlInput);
      setCounterEvidenceUrlInput('');
    } catch (err) {
      console.error(err);
    }
  };

  const handleRequestSalary = async (e) => {
    e.preventDefault();
    if (selectedPayrollId === null) return;
    try {
      await requestSalary(selectedPayrollId, workProofUrlInput, counterEvidenceUrlInput);
      setWorkProofUrlInput('');
      setCounterEvidenceUrlInput('');
    } catch (err) {
      console.error(err);
    }
  };

  const handleReclaimTimedOut = async (payrollId) => {
    try {
      await reclaimTimedOutPayroll(payrollId);
    } catch (err) {
      console.error(err);
    }
  };

  // Compute stat summary metrics
  const paidCount = payrolls.filter(p => p.status === 'PAID').length;
  const slashedCount = payrolls.filter(p => p.status === 'SLASHED').length;

  return (
    <div className="app-container">
      {/* Top Navbar */}
      <header className="navbar">
        <div className="brand-logo" onClick={() => setActiveTab('LANDING')} style={{ cursor: 'pointer' }}>
          <div className="brand-icon-box">
            <Scale size={24} />
          </div>
          <div>
            <div className="brand-title">DAOGuillotine</div>
            <div className="brand-subtitle">AI Contributor Audit & Escrow Protocol</div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div className="nav-links">
            <button 
              onClick={() => setActiveTab('LANDING')}
              className={`nav-link ${activeTab === 'LANDING' ? 'active' : ''}`}
            >
              Overview
            </button>
            <button 
              onClick={() => setActiveTab('CREATE_PAYROLL')}
              className={`nav-link ${activeTab === 'CREATE_PAYROLL' ? 'active' : ''}`}
            >
              Lock Bounty
            </button>
            <button 
              onClick={() => {
                setActiveTab('CABINET');
                fetchPayrollsState();
              }}
              className={`nav-link ${activeTab === 'CABINET' ? 'active' : ''}`}
            >
              Dossiers ({payrolls.length})
            </button>
          </div>

          <div style={{ background: '#111622', border: '1px solid var(--border-color)', borderRadius: '10px', padding: '6px 14px', fontSize: '12px', color: 'var(--primary-cyan)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#10B981', boxShadow: '0 0 8px #10B981' }} />
            StudioNet
          </div>

          {address ? (
            <div style={{ background: 'var(--primary-cyan-dim)', border: '1px solid rgba(0, 240, 255, 0.3)', borderRadius: '10px', padding: '8px 16px', color: '#FFF', fontSize: '13px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Wallet size={16} color="var(--primary-cyan)" />
              {address.slice(0, 6)}...{address.slice(-4)}
            </div>
          ) : (
            <button onClick={connectWallet} className="btn-primary" style={{ width: 'auto', padding: '10px 20px', fontSize: '14px' }}>
              <Wallet size={16} />
              Connect Wallet
            </button>
          )}
        </div>
      </header>

      {/* Modern Web3 Full-Screen Loading Modal Overlay */}
      {loading && (
        <div className="modal-overlay">
          <div className="loading-modal-card">
            <div className="loading-spinner-box">
              <RefreshCw size={44} className="animate-spin" color="var(--primary-cyan)" />
              <div className="spinner-glow-ring" />
            </div>

            <h3 className="loading-modal-title">
              GenLayer AI Consensus in Progress
            </h3>

            <p className="loading-modal-status">
              {txStatus || 'Writing transaction instructions to GenLayer Virtual Machine...'}
            </p>

            <div className="loading-steps-box">
              <div className="loading-step-item">
                <span className="step-dot active" />
                <span>1. Scraping deliverables URL via gl.nondet.web.render</span>
              </div>
              <div className="loading-step-item">
                <span className="step-dot active" />
                <span>2. Executing LLM Tech Lead prompt for effort score</span>
              </div>
              <div className="loading-step-item">
                <span className="step-dot active" />
                <span>3. Re-executing validator nodes for spectrum consensus</span>
              </div>
            </div>

            {txHash && (
              <div className="loading-tx-hash">
                <span>TX HASH:</span> {txHash}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Hero / Landing View */}
      {activeTab === 'LANDING' && (
        <main className="main-content">
          <div className="hero-section">
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', background: 'var(--primary-cyan-dim)', border: '1px solid rgba(0,240,255,0.3)', padding: '6px 14px', borderRadius: '20px', color: 'var(--primary-cyan)', fontSize: '12px', fontWeight: 600, marginBottom: '24px' }}>
              <Zap size={14} />
              GenLayer Intelligent Contract Escrow Protocol
            </div>

            <h1 className="hero-title">
              Autonomous AI Slasher for Web3 Contributor Payrolls
            </h1>

            <p className="hero-description">
              Stop Telegram meeting-spam, corporate fluff, and fake work. DAOGuillotine locks contributor salary/bounties in smart contracts bound to shared, immutable acceptance criteria. GenLayer AI nodes cross-examine deliverables against criteria and DAO counter-evidence, automatically slashing insufficient effort back to the DAO treasury.
            </p>

            <div style={{ display: 'flex', gap: '16px', justifyContent: 'center', marginBottom: '50px' }}>
              <button onClick={() => setActiveTab('CREATE_PAYROLL')} className="btn-primary" style={{ width: 'auto', padding: '14px 32px', fontSize: '15px' }}>
                <PlusCircle size={18} />
                Lock Bounty Escrow
              </button>
              <button onClick={() => { setActiveTab('CABINET'); fetchPayrollsState(); }} className="btn-secondary" style={{ width: 'auto', padding: '14px 32px', fontSize: '15px' }}>
                <FolderOpen size={18} />
                Explore Active Dossiers
              </button>
            </div>

            {/* STUNNING 4-COLUMN HORIZONTAL STATS GRID */}
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-header">
                  <span>VAULT VALUE LOCKED</span>
                  <div className="stat-icon-wrapper">
                    <Coins size={18} color="var(--primary-cyan)" />
                  </div>
                </div>
                <div className="stat-value" style={{ color: 'var(--primary-cyan)' }}>
                  {formatGen(contractBalance)} GEN
                </div>
                <div className="stat-footer">
                  Held in DAOGuillotine Vault
                </div>
              </div>

              <div className="stat-card">
                <div className="stat-header">
                  <span>TOTAL DOSSIERS</span>
                  <div className="stat-icon-wrapper">
                    <FolderOpen size={18} color="#FFF" />
                  </div>
                </div>
                <div className="stat-value">{payrolls.length}</div>
                <div className="stat-footer" style={{ color: '#10B981' }}>
                  {payrolls.filter(p => p.status === 'ACTIVE' || p.status === 'DISPUTED').length} Active Payrolls
                </div>
              </div>

              <div className="stat-card">
                <div className="stat-header">
                  <span>CONTRIBUTORS PAID</span>
                  <div className="stat-icon-wrapper">
                    <ShieldCheck size={18} color="var(--emerald-success)" />
                  </div>
                </div>
                <div className="stat-value" style={{ color: 'var(--emerald-success)' }}>{paidCount}</div>
                <div className="stat-footer">
                  Deliverables Verified
                </div>
              </div>

              <div className="stat-card">
                <div className="stat-header">
                  <span>FLUFF SLASHED</span>
                  <div className="stat-icon-wrapper">
                    <AlertCircle size={18} color="var(--rose-slash)" />
                  </div>
                </div>
                <div className="stat-value" style={{ color: 'var(--rose-slash)' }}>{slashedCount}</div>
                <div className="stat-footer" style={{ color: 'var(--rose-slash)' }}>
                  Refreshed to Treasury
                </div>
              </div>
            </div>

          </div>
        </main>
      )}

      {/* Main App Body */}
      {activeTab !== 'LANDING' && (
        <main className="main-content">
          {!address ? (
            <div className="glass-card" style={{ textAlign: 'center', padding: '60px 30px', maxWidth: '540px', margin: '40px auto' }}>
              <AlertCircle size={48} color="var(--primary-cyan)" style={{ margin: '0 auto 16px auto' }} />
              <h2 style={{ fontFamily: 'var(--font-heading)', color: '#FFF', fontSize: '22px', marginBottom: '10px' }}>
                Web3 Identity Required
              </h2>
              <p style={{ color: 'var(--text-muted)', fontSize: '14px', lineHeight: '22px', marginBottom: '24px' }}>
                Please connect your MetaMask wallet or StudioNet account to lock bounties, submit work proof, or inspect contributor dossiers.
              </p>
              <button onClick={connectWallet} className="btn-primary">
                <Wallet size={18} />
                Connect Wallet Identity
              </button>
            </div>
          ) : (
            <div>
              {error && (
                <div style={{ background: 'var(--rose-dim)', border: '1px solid var(--rose-slash)', color: '#FDA4AF', padding: '14px 20px', borderRadius: '12px', marginBottom: '24px', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <AlertCircle size={18} />
                  <span>{error}</span>
                </div>
              )}

              {/* Tab 1: Create Payroll Form */}
              {activeTab === 'CREATE_PAYROLL' && (
                <div className="glass-card" style={{ maxWidth: '640px', margin: '0 auto', padding: '36px' }}>
                  <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '20px', color: '#FFF', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <PlusCircle size={22} color="var(--primary-cyan)" />
                    Lock Contributor Bounty Escrow
                  </h2>
                  <p style={{ color: 'var(--text-muted)', fontSize: '13px', marginBottom: '28px' }}>
                    Lock native GEN tokens bound to a shared, immutable acceptance criteria policy.
                  </p>

                  <form onSubmit={handleCreatePayroll}>
                    <div className="form-group">
                      <label className="form-label">CONTRIBUTOR WALLET ADDRESS</label>
                      <input 
                        type="text" 
                        placeholder="e.g. 0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
                        value={contributorInput}
                        onChange={(e) => setContributorInput(e.target.value)}
                        className="form-input"
                        required
                      />
                    </div>

                    <div className="form-group">
                      <label className="form-label">BOUNTY / SALARY AMOUNT (GEN)</label>
                      <input 
                        type="number" 
                        step="0.001"
                        min="0.001"
                        placeholder="5.0"
                        value={amountInput}
                        onChange={(e) => setAmountInput(e.target.value)}
                        className="form-input"
                        required
                      />
                    </div>

                    <div className="form-group">
                      <label className="form-label">SHARED, IMMUTABLE ACCEPTANCE CRITERIA URL (REQUIRED)</label>
                      <input 
                        type="text" 
                        placeholder="https://raw.githubusercontent.com/Tannpd/daoguillotine-slasher/main/public/criteria_sprint_1.txt"
                        value={acceptanceCriteriaUrlInput}
                        onChange={(e) => setAcceptanceCriteriaUrlInput(e.target.value)}
                        className="form-input"
                        required
                      />
                      <div style={{ marginTop: '8px' }}>
                        <button
                          type="button"
                          className="preset-btn preset-btn-cyan"
                          style={{ fontSize: '11px', padding: '4px 10px' }}
                          onClick={() => setAcceptanceCriteriaUrlInput('https://raw.githubusercontent.com/Tannpd/daoguillotine-slasher/main/public/criteria_sprint_1.txt')}
                        >
                          + Fill Sample Immutable Acceptance Criteria URL
                        </button>
                      </div>
                    </div>

                    <button type="submit" className="btn-primary" disabled={loading} style={{ marginTop: '10px' }}>
                      {loading ? 'Locking Escrow...' : 'Lock GEN Salary in Vault →'}
                    </button>
                  </form>
                </div>
              )}

              {/* Tab 2: Cabinet Index & View Dossier */}
              {activeTab === 'CABINET' && (
                <div style={{ display: 'grid', gridTemplateColumns: payrolls.length > 0 ? '340px 1fr' : '1fr', gap: '24px' }}>
                  
                  {/* Left Sidebar Drawer Index */}
                  {payrolls.length > 0 ? (
                    <div className="glass-card" style={{ padding: '20px' }}>
                      <div style={{ fontSize: '12px', fontWeight: 'bold', color: 'var(--primary-cyan)', marginBottom: '16px', letterSpacing: '1px' }}>
                        REGISTERED DOSSIERS DRAWER
                      </div>

                      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', maxHeight: '650px', overflowY: 'auto' }}>
                        {payrolls.map((p) => {
                          const isSelected = Number(selectedPayrollId) === Number(p.id);
                          return (
                            <div 
                              key={p.id}
                              className={`payroll-card ${isSelected ? 'selected' : ''}`}
                              onClick={() => setSelectedPayrollId(p.id)}
                            >
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                                <span style={{ fontWeight: 700, fontSize: '14px', color: '#FFF' }}>
                                  Case #{p.id}
                                </span>
                                <span className={`badge ${p.status === 'PAID' ? 'badge-paid' : p.status === 'SLASHED' ? 'badge-slashed' : 'badge-active'}`}>
                                  {p.status}
                                </span>
                              </div>

                              <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                CONTR: {p.contributor}
                              </div>

                              <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--primary-cyan)', marginTop: '8px' }}>
                                {formatGen(p.amount)} GEN
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  ) : (
                    <div className="glass-card" style={{ textAlign: 'center', padding: '60px', color: 'var(--text-muted)' }}>
                      <FolderOpen size={48} style={{ margin: '0 auto 16px auto', opacity: 0.5 }} />
                      <h3>No Contributor Dossiers On-Chain</h3>
                      <p style={{ fontSize: '13px', marginTop: '6px' }}>Lock the first bounty escrow using the "Lock Bounty" tab above.</p>
                    </div>
                  )}

                  {/* Right Dossier Detail View */}
                  <div>
                    {selectedPayroll && (
                      <div className="glass-card" style={{ padding: '32px' }}>
                        
                        {/* Header metadata */}
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', borderBottom: '1px solid var(--border-color)', paddingBottom: '20px' }}>
                          <div>
                            <div style={{ fontSize: '11px', color: 'var(--primary-cyan)', fontWeight: 700, letterSpacing: '1px' }}>
                              INTELLIGENT CONTRACT DOSSIER
                            </div>
                            <div style={{ fontFamily: 'var(--font-heading)', fontSize: '24px', fontWeight: 800, color: '#FFF', marginTop: '4px' }}>
                              Case #{selectedPayroll.id}
                            </div>
                          </div>

                          <span className={`badge ${selectedPayroll.status === 'PAID' ? 'badge-paid' : selectedPayroll.status === 'SLASHED' ? 'badge-slashed' : 'badge-active'}`} style={{ fontSize: '14px', padding: '8px 18px' }}>
                            {selectedPayroll.status === 'PAID' && <CheckCircle2 size={16} />}
                            {selectedPayroll.status === 'SLASHED' && <AlertCircle size={16} />}
                            {selectedPayroll.status === 'ACTIVE' && <Sparkles size={16} />}
                            {selectedPayroll.status}
                          </span>
                        </div>

                        {/* Detail Info Grid */}
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '24px' }}>
                          <div style={{ background: '#090C12', border: '1px solid var(--border-color)', borderRadius: '12px', padding: '14px 18px' }}>
                            <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600 }}>DAO SOURCE (ESCROW OWNER)</div>
                            <div style={{ fontSize: '12px', color: '#FFF', fontFamily: 'var(--font-mono)', marginTop: '4px' }}>{selectedPayroll.dao}</div>
                          </div>

                          <div style={{ background: '#090C12', border: '1px solid var(--border-color)', borderRadius: '12px', padding: '14px 18px' }}>
                            <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600 }}>CONTRIBUTOR RECIPIENT</div>
                            <div style={{ fontSize: '12px', color: '#FFF', fontFamily: 'var(--font-mono)', marginTop: '4px' }}>{selectedPayroll.contributor}</div>
                          </div>
                        </div>

                        <div style={{ background: 'var(--primary-cyan-dim)', border: '1px solid rgba(0, 240, 255, 0.3)', borderRadius: '12px', padding: '16px 20px', marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-muted)' }}>LOCKED ESCROW AMOUNT</span>
                          <span style={{ fontFamily: 'var(--font-heading)', fontSize: '24px', fontWeight: 800, color: 'var(--primary-cyan)' }}>
                            {formatGen(selectedPayroll.amount)} GEN
                          </span>
                        </div>

                        {/* Progress Gauge */}
                        {selectedPayroll.effort_score > 0 && (
                          <div style={{ marginBottom: '24px' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '8px' }}>
                              <span>AI PRODUCTIVITY GAUGED VALUE</span>
                              <span style={{ color: selectedPayroll.is_slashed ? 'var(--rose-slash)' : 'var(--emerald-success)' }}>
                                {selectedPayroll.effort_score}% EFFORT SCORE
                              </span>
                            </div>
                            <div className="progress-bar-track">
                              <div 
                                className={`progress-bar-fill ${selectedPayroll.effort_score >= 50 ? 'high' : 'low'}`}
                                style={{ width: `${selectedPayroll.effort_score}%` }}
                              />
                            </div>
                          </div>
                        )}

                        {/* Audit Decree Box */}
                        {selectedPayroll.audit_report && (
                          <div className={`decree-box ${selectedPayroll.status === 'PAID' ? 'paid' : selectedPayroll.status === 'SLASHED' ? 'slashed' : ''}`}>
                            <div style={{ fontSize: '12px', fontWeight: 700, color: selectedPayroll.status === 'PAID' ? 'var(--emerald-success)' : selectedPayroll.status === 'SLASHED' ? 'var(--rose-slash)' : 'var(--primary-cyan)', display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                              <ShieldCheck size={16} />
                              GENLAYER AI AUDITOR DECREE LOG
                            </div>
                            <div style={{ fontStyle: 'italic', fontSize: '14px', color: '#E2E8F0', lineHeight: '22px' }}>
                              "{selectedPayroll.audit_report}"
                            </div>

                            {selectedPayroll.acceptance_criteria_url && (
                              <div style={{ marginTop: '14px', paddingTop: '10px', borderTop: '1px dashed var(--border-color)', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <span style={{ color: 'var(--text-muted)' }}>AGREED CRITERIA URL:</span>
                                <a 
                                  href={selectedPayroll.acceptance_criteria_url} 
                                  target="_blank" 
                                  rel="noreferrer" 
                                  style={{ color: 'var(--primary-cyan)', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                                >
                                  {selectedPayroll.acceptance_criteria_url}
                                  <ExternalLink size={12} />
                                </a>
                              </div>
                            )}

                            {selectedPayroll.work_proof_url && (
                              <div style={{ marginTop: '8px', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <span style={{ color: 'var(--text-muted)' }}>WORK PROOF URL:</span>
                                <a 
                                  href={selectedPayroll.work_proof_url} 
                                  target="_blank" 
                                  rel="noreferrer" 
                                  style={{ color: 'var(--primary-cyan)', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                                >
                                  {selectedPayroll.work_proof_url}
                                  <ExternalLink size={12} />
                                </a>
                              </div>
                            )}

                            {selectedPayroll.counter_evidence_url && (
                              <div style={{ marginTop: '8px', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <span style={{ color: 'var(--rose-slash)' }}>DAO COUNTER-EVIDENCE:</span>
                                <a 
                                  href={selectedPayroll.counter_evidence_url} 
                                  target="_blank" 
                                  rel="noreferrer" 
                                  style={{ color: 'var(--rose-slash)', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                                >
                                  {selectedPayroll.counter_evidence_url}
                                  <ExternalLink size={12} />
                                </a>
                              </div>
                            )}
                          </div>
                        )}

                        {/* Action Form */}
                        <div style={{ marginTop: '32px', paddingTop: '24px', borderTop: '1px solid var(--border-color)' }}>
                          {selectedPayroll.status === 'ACTIVE' || selectedPayroll.status === 'DISPUTED' || selectedPayroll.status === 'FAILED' ? (
                            <div>
                              <div>
                                <div style={{ background: 'var(--primary-cyan-dim)', border: '1px solid rgba(0, 240, 255, 0.3)', borderRadius: '12px', padding: '14px 18px', fontSize: '13px', color: '#A5F3FC', marginBottom: '20px' }}>
                                  Authenticated Role Recognized // Contributor or DAO Admin. Submit work proof to open Challenge Window, attach counter-evidence, or trigger AI Audit.
                                </div>

                                {/* Preset Fill Buttons */}
                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', marginBottom: '20px' }}>
                                  <button
                                    type="button"
                                    className="preset-btn preset-btn-cyan"
                                    onClick={() => {
                                      setWorkProofUrlInput('https://raw.githubusercontent.com/Tannpd/daoguillotine-slasher/main/public/mock_report_solid_work.txt');
                                    }}
                                  >
                                    <Sparkles size={14} />
                                    + Fill Solid Work Report (Payout)
                                  </button>

                                  <button
                                    type="button"
                                    className="preset-btn preset-btn-rose"
                                    onClick={() => {
                                      setWorkProofUrlInput('https://raw.githubusercontent.com/Tannpd/daoguillotine-slasher/main/public/mock_report_fluff_meetings.txt');
                                    }}
                                  >
                                    <AlertCircle size={14} />
                                    + Fill Fluff Meetings Report (Slash DAO)
                                  </button>

                                  <button
                                    type="button"
                                    className="preset-btn preset-btn-rose"
                                    onClick={() => {
                                      setCounterEvidenceUrlInput('https://raw.githubusercontent.com/Tannpd/daoguillotine-slasher/main/public/counter_evidence_bug_log.txt');
                                    }}
                                  >
                                    <Shield size={14} />
                                    + Fill DAO Dispute Report (Counter-Evidence)
                                  </button>
                                </div>

                                {/* Multi-stage Action Box */}
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                                  
                                  {/* STAGE 1: SUBMIT WORK PROOF */}
                                  <form onSubmit={handleSubmitWorkProof} style={{ background: '#090C12', border: '1px solid var(--border-color)', borderRadius: '12px', padding: '20px' }}>
                                    <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--primary-cyan)', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                      <FileCode size={16} />
                                      STAGE 1: SUBMIT WORK PROOF & OPEN DAO CHALLENGE WINDOW
                                    </div>
                                    <div className="form-group">
                                      <input 
                                        type="text" 
                                        placeholder="https://raw.githubusercontent.com/Tannpd/daoguillotine-slasher/main/public/mock_report_solid_work.txt" 
                                        value={workProofUrlInput}
                                        onChange={(e) => setWorkProofUrlInput(e.target.value)}
                                        className="form-input"
                                        required
                                      />
                                    </div>
                                    <button type="submit" className="btn-primary" disabled={loading || selectedPayroll.audit_opened}>
                                      Submit Work Proof (Stage 1) →
                                    </button>
                                  </form>

                                  {/* STAGE 2: SUBMIT COUNTER EVIDENCE */}
                                  <form onSubmit={handleSubmitCounterEvidence} style={{ background: '#090C12', border: '1px dashed var(--rose-slash)', borderRadius: '12px', padding: '20px' }}>
                                    <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--rose-slash)', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                      <Shield size={16} />
                                      DAO CHALLENGE WINDOW: SUBMIT COUNTER-EVIDENCE
                                    </div>
                                    <div className="form-group">
                                      <input 
                                        type="text" 
                                        placeholder="https://raw.githubusercontent.com/Tannpd/daoguillotine-slasher/main/public/counter_evidence_bug_log.txt" 
                                        value={counterEvidenceUrlInput}
                                        onChange={(e) => setCounterEvidenceUrlInput(e.target.value)}
                                        className="form-input"
                                        required
                                      />
                                    </div>
                                    <button type="submit" className="btn-secondary" style={{ borderColor: 'var(--rose-slash)', color: '#FDA4AF' }} disabled={loading || selectedPayroll.audit_opened}>
                                      Attach DAO Counter-Evidence →
                                    </button>
                                  </form>

                                  {/* STAGE 3: TRIGGER AI AUDIT & RECLAIM */}
                                  <div style={{ display: 'flex', gap: '12px' }}>
                                    <button onClick={handleRequestSalary} className="btn-primary" disabled={loading || selectedPayroll.audit_opened} style={{ flex: 1 }}>
                                      {loading ? (
                                        <>
                                          <RefreshCw size={18} className="animate-spin" />
                                          Auditing Deliverables via AI Nodes...
                                        </>
                                      ) : (
                                        <>
                                          <ShieldCheck size={18} />
                                          Trigger AI Audit & Lock Evidence
                                        </>
                                      )}
                                    </button>

                                    <button 
                                      type="button" 
                                      className="btn-primary" 
                                      onClick={() => handleReclaimTimedOut(selectedPayroll.id)}
                                      disabled={loading}
                                      style={{ background: 'var(--rose-dim)', border: '1px solid var(--rose-slash)', color: '#FDA4AF', width: 'auto', padding: '0 20px' }}
                                    >
                                      Reclaim Timed Out Deposit
                                    </button>
                                  </div>

                                </div>
                              </div>
                            </div>
                          ) : (
                            <div style={{ background: '#090C12', padding: '20px', borderRadius: '12px', border: '1px solid var(--border-color)', color: 'var(--text-muted)', textAlign: 'center', fontSize: '13px' }}>
                              Dossier Finalized. Payout settled, slashed, or reclaimed on-chain.
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </main>
      )}
    </div>
  );
}
