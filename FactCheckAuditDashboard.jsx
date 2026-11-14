import React, { useState, useMemo, useRef, useEffect } from "react";

// ============================================================================
// Verdict System Configuration (Uniform Categorization)
// ============================================================================
const VERDICT_CONFIG = {
  VERIFIED: {
    label: "VERIFIED",
    textClass: "text-emerald-400",
    bgClass: "bg-emerald-500/10",
    borderClass: "border-emerald-500/30",
    glowClass: "shadow-[0_0_12px_rgba(16,185,129,0.18)]",
    cardBorder: "border-l-emerald-500",
    accentHex: "#10B981"
  },
  FALSE: {
    label: "FALSE",
    textClass: "text-rose-400",
    bgClass: "bg-rose-500/10",
    borderClass: "border-rose-500/30",
    glowClass: "shadow-[0_0_12px_rgba(239,68,68,0.18)]",
    cardBorder: "border-l-rose-500",
    accentHex: "#EF4444"
  },
  MISLEADING: {
    label: "MISLEADING",
    textClass: "text-amber-400",
    bgClass: "bg-amber-500/10",
    borderClass: "border-amber-500/30",
    glowClass: "shadow-[0_0_12px_rgba(245,158,11,0.18)]",
    cardBorder: "border-l-amber-500",
    accentHex: "#F59E0B"
  },
  EXAGGERATION: {
    label: "EXAGGERATION",
    textClass: "text-purple-400",
    bgClass: "bg-purple-500/10",
    borderClass: "border-purple-500/30",
    glowClass: "shadow-[0_0_12px_rgba(168,85,247,0.22)]",
    cardBorder: "border-l-purple-500",
    accentHex: "#A855F7"
  }
};

// ============================================================================
// Verification API Configuration
// ============================================================================
const VERIFICATION_API_BASE = "/api/verify-claim";

// ============================================================================
// Default Audit Dataset (Inspired by MrBeast Futuristic Tech Audit)
// ============================================================================
const DEFAULT_AUDIT_DATA = {
  title: "MrBeast • $1 vs $1,000,000,000 Futuristic Tech!",
  genre: "ENTERTAINMENT & STUNTS",
  summary:
    "A high-production value entertainment video showcasing real-world emerging technologies through the lens of MrBeast's signature challenge-based format, blending genuine scientific demonstrations with staged dramatic stunts.",
  clickbaitIndex: 15,
  clickbaitLabel: "Low Clickbait",
  reliabilityScore: 88,
  sources: [
    { name: "Nature", subLabel: "Nature News & Analysis", url: "https://www.nature.com" },
    { name: "Bureau of Transportation Statistics", subLabel: "US Department of Transportation", url: "https://www.bts.gov" },
    { name: "Automotive News", subLabel: "Industry Market Analysis", url: "https://www.autonews.com" },
    { name: "IEEE Spectrum", subLabel: "Emerging Robotics Benchmarks", url: "https://spectrum.ieee.org" },
    { name: "MIT Technology Review", subLabel: "Autonomous Systems Dossier", url: "https://www.technologyreview.com" },
    { name: "Federal Aviation Administration", subLabel: "FAA Experimental Airworthiness", url: "https://www.faa.gov" }
  ],
  claims: [
    {
      id: "claim-1",
      timestamp: "00:44",
      seconds: 44,
      verdict: "VERIFIED",
      quote: "This solar-powered hypercar charges while driving in direct sunlight.",
      explanation:
        "Lightyear & Aptera solar integration specs verify solar trickle charging adds ~40 miles/day in optimal daylight conditions.",
      authority: "Nature / Department of Transportation",
      citation: "Nature Energy Journal, Vol 7: Integrated Photovoltaic Mobility",
      finding: "Empirically validated solar photovoltaic rooftop modules generate sufficient trickle wattage for low-draw cruise assistance.",
      origin: "National Renewable Energy Laboratory (NREL)"
    },
    {
      id: "claim-2",
      timestamp: "04:07",
      seconds: 247,
      verdict: "EXAGGERATION",
      quote: "I'd save like a thousand hours a year.",
      explanation:
        "Comedic hyperbole regarding autonomous commuting efficiency. In reality, the average US commuter spends approximately 240 to 300 hours traveling annually.",
      authority: "Bureau of Transportation Statistics",
      citation: "DOT National Household Travel Survey (NHTS) 2023",
      finding: "Annual commuter hour savings for typical metropolitan drivers average 254 hours/year, making 1,000 hours a creative dramatic exaggeration.",
      origin: "US Department of Transportation"
    },
    {
      id: "claim-3",
      timestamp: "05:57",
      seconds: 357,
      verdict: "EXAGGERATION",
      quote: "This humanoid robot is literally smarter than any human on Earth.",
      explanation:
        "Entertainment hyperbole highlighting agile humanoid motion. The robot operates under predetermined kinematic trajectory constraints and teleoperation safeguards.",
      authority: "IEEE Spectrum / Robotics Society",
      citation: "IEEE International Conference on Robotics and Automation (ICRA)",
      finding: "Demonstrated mobility utilizes balance stabilization algorithms; cognitive generalized intelligence remains domain-bounded.",
      origin: "IEEE Global Robotics Database"
    },
    {
      id: "claim-4",
      timestamp: "08:06",
      seconds: 486,
      verdict: "VERIFIED",
      quote: "This exoskeleton multiplies human lifting strength by 20 times.",
      explanation:
        "Industrial powered exoskeletons (such as the Sarcos Guardian XO) deliver a tested 20:1 strength amplification ratio under powered pneumatic assist.",
      authority: "MIT Technology Review / OSHA",
      citation: "Occupational Safety & Health Ergonomics Assessment Standard 2024",
      finding: "Full-body powered exoskeletons successfully offload up to 95% of vertical load stress from the human lumbar spine.",
      origin: "MIT Technology Review Emerging Systems"
    },
    {
      id: "claim-5",
      timestamp: "10:22",
      seconds: 622,
      verdict: "VERIFIED",
      quote: "The battery pack in this electric jet charges from 10% to 80% in 15 minutes.",
      explanation:
        "Verified against 800V fast-charging aviation battery packs tested under FAA experimental airworthiness protocols and active liquid-cooling chillers.",
      authority: "FAA / IEEE Aerospace",
      citation: "FAA Special Airworthiness Information Bulletin (SAIB) No. AIR-23-14",
      finding: "High-density silicon-anode cells with active immersion cooling successfully sustained 350kW continuous DC fast-charging rates.",
      origin: "Federal Aviation Administration Registry"
    },
    {
      id: "claim-6",
      timestamp: "19:49",
      seconds: 1189,
      verdict: "VERIFIED",
      quote: "This submarine drone can dive over 3,000 feet deep with 4K telemetry.",
      explanation:
        "Commercial deep-sea exploration ROVs routinely operate at depth ratings exceeding 1,000 meters (3,280 ft) using fiber-optic tethered umbilicals.",
      authority: "National Oceanic and Atmospheric Administration",
      citation: "NOAA Ocean Exploration Technical Report: ROV Deep Submergence Specs",
      finding: "Syntactic foam buoyancy modules and titanium pressure vessels maintain hermetic integrity to depths beyond 1,200 meters.",
      origin: "Woods Hole Oceanographic Institution"
    }
  ]
};

// ============================================================================
// Main Fact-Check Audit Component
// ============================================================================
export default function FactCheckAuditDashboard({ data = DEFAULT_AUDIT_DATA, onSeekTimestamp }) {
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const [activeFilter, setActiveFilter] = useState("ALL"); // ALL, FALSE, VERIFIED, EXAGGERATION
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedDrawers, setExpandedDrawers] = useState({});
  const [highlightedClaimId, setHighlightedClaimId] = useState(null);

  // Calculate Metrics
  const counts = useMemo(() => {
    const res = { FALSE: 0, VERIFIED: 0, MISLEADING: 0, EXAGGERATION: 0 };
    data.claims.forEach((c) => {
      if (res[c.verdict] !== undefined) res[c.verdict]++;
    });
    return res;
  }, [data.claims]);

  // Verification State
  const [isVerifying, setIsVerifying] = useState(false);
  const [verificationResult, setVerificationResult] = useState(null);
  const [verifyingClaim, setVerifyingClaim] = useState(null);

  // Verify Claim
  const verifyClaim = async (claim) => {
    setIsVerifying(true);
    setVerifyingClaim(claim);
    setVerificationResult(null);

    try {
      const res = await fetch("/api/verify-claim", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          claim_text: claim.quote,
          claim_timestamp: claim.timestamp,
          video_context_summary: data.genre || "General Video",
          retrieved_search_snippets: "",
        }),
      });

      const result = await res.json();
      setVerificationResult(result);
    } catch (e) {
      setVerificationResult({
        status: "UNVERIFIED",
        confidence_score: 0.0,
        is_satire: false,
        explanation: "Error connecting to verification service.",
        audited_sources: [],
      });
    } finally {
      setIsVerifying(false);
      setVerifyingClaim(null);
    }
  };

  // Filter Claims
  const filteredClaims = useMemo(() => {
    const q = searchQuery.toLowerCase().trim();
    return data.claims.filter((c) => {
      const matchesFilter = activeFilter === "ALL" || c.verdict === activeFilter;
      const matchesQuery =
        !q ||
        c.quote.toLowerCase().includes(q) ||
        c.explanation.toLowerCase().includes(q) ||
        c.authority.toLowerCase().includes(q) ||
        c.timestamp.includes(q);
      return matchesFilter && matchesQuery;
    });
  }, [data.claims, activeFilter, searchQuery]);

  // Toggle Source Drawer for a card
  const toggleDrawer = (claimId) => {
    setExpandedDrawers((prev) => ({
      ...prev,
      [claimId]: !prev[claimId]
    }));
  };

  // Jump to claim via timestamp
  const handleJumpToClaim = (claim) => {
    setHighlightedClaimId(claim.id);
    if (onSeekTimestamp) {
      onSeekTimestamp(claim.seconds);
    }
    const targetEl = document.getElementById(`audit-card-${claim.id}`);
    if (targetEl) {
      targetEl.scrollIntoView({ behavior: "smooth", block: "center" });
    }
    setTimeout(() => setHighlightedClaimId(null), 2400);
  };

  return (
    <div className="w-full max-w-xl mx-auto bg-[#0B0F19] text-slate-100 rounded-2xl border border-white/10 shadow-2xl p-5 font-sans transition-all duration-300">
      
      {/* =====================================================================
          1. Header & Topic Intel
          ===================================================================== */}
      <section className="mb-5 pb-5 border-b border-white/[0.08]">
        <div className="flex items-center justify-between gap-3 mb-2.5">
          <span className="text-[10px] font-mono font-semibold tracking-wider uppercase text-blue-400 bg-blue-500/10 border border-blue-500/20 px-2 py-0.5 rounded">
            Topic Intel
          </span>

          {data.genre && (
            <span className="text-[10px] font-mono font-bold tracking-wide uppercase px-2.5 py-1 rounded bg-purple-500/15 text-purple-300 border border-purple-500/30 flex items-center gap-1.5 shadow-[0_0_10px_rgba(168,85,247,0.15)]">
              <span>🎭</span>
              <span>{data.genre}</span>
            </span>
          )}
        </div>

        <h2 className="text-base font-semibold text-white tracking-tight mb-2 flex items-center gap-1.5">
          <span className="text-blue-400">{data.title.split("•")[0]}</span>
          {data.title.includes("•") && <span className="text-slate-500">•</span>}
          <span>{data.title.split("•")[1] || ""}</span>
        </h2>

        <p className="text-xs text-slate-400 leading-relaxed mb-3">
          {data.summary}
        </p>

        {data.clickbaitIndex !== undefined && (
          <div className="inline-flex items-center gap-1.5 text-[11px] font-mono font-semibold px-2.5 py-1 rounded-md bg-amber-500/10 text-amber-300 border border-amber-500/25">
            <span>🎯</span>
            <span>Clickbait Index: {data.clickbaitIndex}% ({data.clickbaitLabel})</span>
          </div>
        )}
      </section>

      {/* =====================================================================
          2. Audited Sources Accordion
          ===================================================================== */}
      {data.sources && data.sources.length > 0 && (
        <section className="mb-5 bg-white/[0.02] border border-white/[0.08] rounded-xl overflow-hidden">
          <button
            type="button"
            onClick={() => setSourcesOpen(!sourcesOpen)}
            className="w-full px-3.5 py-2.5 flex items-center justify-between text-xs font-medium text-slate-300 hover:text-white hover:bg-white/[0.03] transition-colors"
          >
            <div className="flex items-center gap-2">
              <span className="text-blue-400">📖</span>
              <span>Audited Sources & Citations ({data.sources.length})</span>
            </div>
            <span className="text-[10px] font-mono text-slate-500">
              {sourcesOpen ? "▲" : "▼"}
            </span>
          </button>

          {sourcesOpen && (
            <div className="p-2.5 bg-black/40 border-t border-white/[0.08] flex flex-col gap-1.5">
              {data.sources.map((src, i) => (
                <a
                  key={i}
                  href={src.url || "#"}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between px-3 py-2 rounded-lg bg-white/[0.03] hover:bg-blue-500/10 border border-white/[0.05] hover:border-blue-500/30 text-xs text-slate-200 transition-all duration-150 group"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-blue-400 text-sm">🌐</span>
                    <strong className="font-semibold text-slate-100 group-hover:text-blue-300">
                      {src.name}
                    </strong>
                  </div>
                  <span className="text-[10.5px] font-mono text-slate-500 group-hover:text-slate-400 flex items-center gap-1">
                    {src.subLabel} <span className="text-[10px]">↗</span>
                  </span>
                </a>
              ))}
            </div>
          )}
        </section>
      )}

      {/* =====================================================================
          3. Truth Reliability Bar
          ===================================================================== */}
      <section className="mb-5">
        <div className="flex items-center justify-between text-xs mb-1.5">
          <span className="text-slate-400 font-medium">Truth Reliability</span>
          <span className="font-mono font-bold text-emerald-400 text-sm drop-shadow-[0_0_8px_rgba(16,185,129,0.3)]">
            {data.reliabilityScore}%
          </span>
        </div>
        <div className="w-full h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-rose-500 via-amber-400 to-emerald-400 rounded-full transition-all duration-700 ease-out shadow-[0_0_12px_rgba(16,185,129,0.4)]"
            style={{ width: `${data.reliabilityScore}%` }}
          />
        </div>
      </section>

      {/* =====================================================================
          4. Timeline & Stats Bar
          ===================================================================== */}
      <section className="mb-5 bg-white/[0.02] border border-white/[0.08] rounded-xl p-3.5">
        {/* Metric Counter Row */}
        <div className="flex items-center justify-between flex-wrap gap-2 text-[10.5px] font-mono font-bold uppercase tracking-wider mb-3 pb-2.5 border-b border-white/[0.06]">
          <span className="text-rose-400">{counts.FALSE} FALSE</span>
          <span className="text-emerald-400">{counts.VERIFIED} VERIFIED</span>
          <span className="text-amber-400">{counts.MISLEADING} MISLEADING</span>
          <span className="text-purple-400">{counts.EXAGGERATION} EXAGGERATION</span>
        </div>

        {/* Interactive Timestamp Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none">
          {data.claims.map((c) => {
            const conf = VERDICT_CONFIG[c.verdict] || VERDICT_CONFIG.VERIFIED;
            const matchesActiveFilter = activeFilter === "ALL" || c.verdict === activeFilter;
            return (
              <button
                key={c.id}
                type="button"
                onClick={() => handleJumpToClaim(c)}
                title={`${c.timestamp} - [${conf.label}] ${c.quote}`}
                className={`text-[10px] font-mono font-bold px-2.5 py-1 rounded-md border transition-all duration-200 shrink-0 ${
                  conf.textClass
                } ${conf.bgClass} ${conf.borderClass} ${
                  matchesActiveFilter
                    ? "opacity-100 hover:scale-105 hover:brightness-125"
                    : "opacity-25 grayscale scale-95"
                } ${highlightedClaimId === c.id ? "ring-2 ring-blue-400 brightness-150" : ""}`}
              >
                {c.timestamp}
              </button>
            );
          })}
        </div>
      </section>

      {/* =====================================================================
          5. Interactive Filter Tabs & Search
          ===================================================================== */}
      <section className="mb-4 space-y-2.5">
        {/* Uniform Filter Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
          <button
            type="button"
            onClick={() => setActiveFilter("ALL")}
            className={`text-xs font-medium px-3 py-1.5 rounded-full border transition-all duration-150 shrink-0 ${
              activeFilter === "ALL"
                ? "bg-blue-600 text-white border-blue-500 shadow-[0_0_12px_rgba(59,130,246,0.4)]"
                : "bg-white/[0.04] text-slate-400 border-white/[0.08] hover:text-white hover:bg-white/[0.08]"
            }`}
          >
            All ({data.claims.length})
          </button>

          <button
            type="button"
            onClick={() => setActiveFilter("FALSE")}
            className={`text-xs font-medium px-3 py-1.5 rounded-full border transition-all duration-150 shrink-0 flex items-center gap-1 ${
              activeFilter === "FALSE"
                ? "bg-rose-500/25 text-rose-300 border-rose-500/60 shadow-[0_0_12px_rgba(239,68,68,0.3)] font-semibold"
                : "bg-white/[0.04] text-slate-400 border-white/[0.08] hover:text-rose-300 hover:bg-rose-500/10"
            }`}
          >
            <span>❌</span> False ({counts.FALSE})
          </button>

          <button
            type="button"
            onClick={() => setActiveFilter("VERIFIED")}
            className={`text-xs font-medium px-3 py-1.5 rounded-full border transition-all duration-150 shrink-0 flex items-center gap-1 ${
              activeFilter === "VERIFIED"
                ? "bg-emerald-500/25 text-emerald-300 border-emerald-500/60 shadow-[0_0_12px_rgba(16,185,129,0.3)] font-semibold"
                : "bg-white/[0.04] text-slate-400 border-white/[0.08] hover:text-emerald-300 hover:bg-emerald-500/10"
            }`}
          >
            <span>✅</span> Verified ({counts.VERIFIED})
          </button>

          <button
            type="button"
            onClick={() => setActiveFilter("EXAGGERATION")}
            className={`text-xs font-medium px-3 py-1.5 rounded-full border transition-all duration-150 shrink-0 flex items-center gap-1 ${
              activeFilter === "EXAGGERATION"
                ? "bg-purple-500/25 text-purple-300 border-purple-500/60 shadow-[0_0_12px_rgba(168,85,247,0.3)] font-semibold"
                : "bg-white/[0.04] text-slate-400 border-white/[0.08] hover:text-purple-300 hover:bg-purple-500/10"
            }`}
          >
            <span>🟣</span> Exaggeration ({counts.EXAGGERATION})
          </button>
        </div>

        {/* Quick Search Capsule */}
        <div className="relative">
          <span className="absolute left-3 top-2.5 text-slate-500 text-xs">🔍</span>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search claims (e.g. solar, commute, robot, hours)..."
            className="w-full bg-white/[0.03] border border-white/[0.08] focus:border-blue-500 focus:bg-white/[0.05] rounded-xl pl-8 pr-3 py-2 text-xs text-white placeholder-slate-500 outline-none transition-all duration-150"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery("")}
              className="absolute right-3 top-2.5 text-slate-400 hover:text-white text-xs"
            >
              ✕
            </button>
          )}
        </div>
      </section>

      {/* =====================================================================
          6. Claim Cards List (Visual Flow & Uniform Exaggeration Badge)
          ===================================================================== */}
      <section className="space-y-3">
        {filteredClaims.length === 0 ? (
          <div className="text-center py-10 px-4 bg-white/[0.02] border border-white/[0.06] rounded-xl text-slate-500 text-xs">
            No claims match your active filter or search criteria.
          </div>
        ) : (
          filteredClaims.map((claim) => {
            const conf = VERDICT_CONFIG[claim.verdict] || VERDICT_CONFIG.VERIFIED;
            const isDrawerOpen = !!expandedDrawers[claim.id];
            const isTargeted = highlightedClaimId === claim.id;

            return (
              <article
                key={claim.id}
                id={`audit-card-${claim.id}`}
                className={`bg-[#121622]/90 border border-white/[0.08] border-l-4 ${
                  conf.cardBorder
                } rounded-xl p-4 transition-all duration-200 relative ${
                  isTargeted
                    ? "ring-2 ring-blue-400 shadow-[0_0_24px_rgba(59,130,246,0.3)] scale-[1.01]"
                    : "hover:border-white/20"
                }`}
              >
                {/* Top Row: Timestamp Chip & Status Badge */}
                <div className="flex items-center justify-between mb-2">
                  <button
                    type="button"
                    onClick={() => handleJumpToClaim(claim)}
                    className="text-[11px] font-mono text-slate-400 bg-white/[0.04] hover:bg-blue-500/20 hover:text-blue-300 border border-white/[0.08] px-2 py-0.5 rounded transition-colors"
                  >
                    ⏱ {claim.timestamp}
                  </button>

                  <span
                    className={`text-[10px] font-mono font-bold tracking-wider uppercase px-2.5 py-0.5 rounded border ${conf.textClass} ${conf.bgClass} ${conf.borderClass} ${conf.glowClass}`}
                  >
                    {conf.label}
                  </span>

                  {/* Verify Button */}
                  {isVerifying && verifyingClaim === claim ? (
                    <span className="text-[9px] font-mono text-emerald-300">Verifying...</span>
                  ) : (
                    <button
                      type="button"
                      onClick={() => verifyClaim(claim)}
                      className="text-[9px] font-mono font-bold text-emerald-400 bg-white/[0.04] hover:bg-emerald-500/20 hover:text-emerald-300 border border-emerald-500/30 px-2 py-0.5 rounded transition-colors"
                      title="Verify this claim against live search evidence"
                    >
                      ✓ Verify
                    </button>
                  )}
                </div>
                <div className="flex items-center justify-between mb-2">
                  <button
                    type="button"
                    onClick={() => handleJumpToClaim(claim)}
                    className="text-[11px] font-mono text-slate-400 bg-white/[0.04] hover:bg-blue-500/20 hover:text-blue-300 border border-white/[0.08] px-2 py-0.5 rounded transition-colors"
                  >
                    ⏱ {claim.timestamp}
                  </button>

                  <span
                    className={`text-[10px] font-mono font-bold tracking-wider uppercase px-2.5 py-0.5 rounded border ${conf.textClass} ${conf.bgClass} ${conf.borderClass} ${conf.glowClass}`}
                  >
                    {conf.label}
                  </span>
                </div>

                {/* Quoted Speaker Claim */}
                <blockquote className="italic font-serif text-slate-100 text-[13px] leading-snug mb-2 pl-2.5 border-l-2 border-white/20">
                  "{claim.quote}"
                </blockquote>

                {/* Audit Explanation */}
                <p className="text-xs text-slate-300 leading-relaxed mb-2.5">
                  {claim.explanation}
                </p>

                {/* Authority Tag */}
                <div className="text-[11px] text-slate-400 mb-2">
                  Authority: <strong className="text-blue-400 font-semibold">{claim.authority}</strong>
                </div>

                {/* Expandable Citation Drawer Button */}
                <button
                  type="button"
                  onClick={() => toggleDrawer(claim.id)}
                  className="w-full flex items-center justify-between text-[11px] font-medium text-slate-400 hover:text-slate-200 py-1.5 px-2 rounded-lg bg-white/[0.02] hover:bg-white/[0.05] border border-white/[0.06] transition-colors"
                >
                  <span>Evidence & Source</span>
                  <span className="text-[9px] font-mono text-slate-500">
                    {isDrawerOpen ? "▲" : "▼"}
                  </span>
                </button>

                {/* Expanded Research Drawer */}
                {isDrawerOpen && (
                  <div className="mt-2 p-3 bg-black/40 border border-white/[0.08] rounded-lg text-[11px] text-slate-300 space-y-1.5 animate-fadeIn">
                    {claim.citation && (
                      <div>
                        <strong className="text-slate-400">Citation: </strong>
                        <span>{claim.citation}</span>
                      </div>
                    )}
                    <div>
                      <strong className="text-slate-400">Finding / Analysis: </strong>
                      <span>{claim.finding}</span>
                    </div>
                    <div>
                      <strong className="text-blue-400">Origin: </strong>
                      <span className="text-slate-300">{claim.origin}</span>
                    </div>
                    <a
                      href={`https://www.google.com/search?q=${encodeURIComponent(
                        claim.authority + " " + (claim.citation || claim.quote)
                      )}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 mt-2 px-2.5 py-1 rounded bg-blue-500/15 text-blue-300 border border-blue-500/30 hover:bg-blue-500/25 transition-colors text-[10.5px] font-semibold"
                    >
                      <span>Verify Source ({claim.authority})</span>
                      <span>↗</span>
                    </a>
                  </div>
                </div>

                {/* Verification Result Overlay */}
                {verificationResult && verificationResult.claim_id === claim.id && (
                  <div className="mt-3 p-3 bg-white/[0.02] border border-white/[0.06] rounded-xl">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-emerald-400 font-medium text-sm">
                        {verificationResult.status}
                      </span>
                      <button
                        type="button"
                        onClick={() => setVerificationResult(null)}
                        className="text-[10px] font-mono text-slate-400 hover:text-white cursor-pointer"
                        >
                          ✕
                        </button>
                    </div>
                    <p className="text-xs text-slate-300 leading-relaxed">
                      {verificationResult.explanation}
                    </p>
                    {verificationResult.audited_sources && verificationResult.audited_sources.length > 0 && (
                      <div className="mt-2 text-[9px] text-slate-500">
                        <strong>Sources: </strong>
                        {verificationResult.audited_sources.map((src, i) => (
                          <a
                            key={i}
                            href={src.url || "#"}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="underline text-slate-400 hover:text-emerald-300"
                          >
                            {src.source_name}
                          </a>
                          {i < verificationResult.audited_sources.length - 1 && " • "}
                        ))}
                      </div>
                    )}
                    <div className="mt-2 flex gap-2">
                      <span
                        className={`text-[9px] font-mono font-bold rounded px-2 py-0.5 ${
                          verificationResult.status === "VERIFIED"
                            ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/30"
                            : verificationResult.status === "FALSE"
                            ? "bg-rose-500/20 text-rose-300 border-rose-500/30"
                            : verificationResult.status === "MISLEADING"
                            ? "bg-amber-500/20 text-amber-300 border-amber-500/30"
                            : "bg-purple-500/20 text-purple-300 border-purple-500/30"
                        }`}
                      >
                        {verificationResult.status}
                      </span>
                      <span className="text-[9px] text-slate-500">{Math.round(verificationResult.confidence_score * 100)}% confidence</span>
                    </div>
                  </div>
                )}
              </article>
            );
          })
        )}
      </section>
    </div>
  );
}

