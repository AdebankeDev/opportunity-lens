import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  ArrowRight, ArrowUpRight, Bell, BookOpen, Check, CheckCircle2, ChevronRight,
  ClipboardCheck, Compass, ExternalLink, FileCheck2, FileSearch, FolderOpen,
  GraduationCap, Heart, KeyRound, LayoutDashboard, LockKeyhole, Menu,
  Search, Settings, ShieldCheck, Sparkles, UserCircle2, WandSparkles,
  X, AlertCircle, Clock3, CircleCheck, Info, Landmark
} from "lucide-react";
import "./styles.css";

const MENU = [
  { id: "overview", name: "Overview", icon: LayoutDashboard },
  { id: "discover", name: "Discover", icon: Compass },
  { id: "analyze", name: "Analyze scholarship", icon: FileSearch },
  { id: "profile", name: "My profile", icon: UserCircle2 },
  { id: "checklist", name: "My checklist", icon: ClipboardCheck },
  { id: "settings", name: "Settings", icon: Settings },
];
const INITIAL_PROFILE = {
  full_name: "", country: "Nigeria", institution: "", course_of_study: "",
  academic_level: "", cgpa: "", cgpa_scale: "5", age: "",
};
const SOURCES = [
  { name: "Federal Ministry of Education", desc: "Official federal scholarship announcements and application information.", url: "https://scholarship.education.gov.ng/", icon: Landmark },
  { name: "PTDF Scholarship Portal", desc: "Petroleum Technology Development Fund scholarship announcements.", url: "https://scholarship.ptdf.gov.ng/", icon: GraduationCap },
  { name: "DAAD Scholarships", desc: "Explore international study opportunities and funding programs.", url: "https://www.daad.de/en/studying-in-germany/scholarships/", icon: BookOpen },
];
const LEVELS = ["Undergraduate", "Masters", "PhD", "Secondary school", "Other"];
const formatStatus = (str) => ({
  LIKELY_ELIGIBLE: "Likely eligible",
  POTENTIALLY_ELIGIBLE: "Potentially eligible",
  LIKELY_INELIGIBLE: "Requirements not met",
  INSUFFICIENT_INFORMATION: "More information needed",
  MET: "Met", NOT_MET: "Not met",
  NEEDS_VERIFICATION: "Verify", NOT_SPECIFIED: "Not specified"
}[str] || String(str || "").replaceAll("_", " ").toLowerCase());
function profileForApi(profile) {
  return {
    ...profile, cgpa: profile.cgpa === "" ? null : Number(profile.cgpa),
    cgpa_scale: profile.cgpa_scale === "" ? null : Number(profile.cgpa_scale),
    age: profile.age === "" ? null : Number(profile.age),
  };
}
async function apiPost(path, payload, apiKey) {
  const headers = { "Content-Type": "application/json" };
  if (apiKey) headers["X-Gemini-API-Key"] = apiKey;
  const response = await fetch("/api/" + path, {
    method: "POST", headers, body: JSON.stringify(payload)
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "Request failed. Please try again.");
  return data;
}
const split = (s) => s.split(/[,;\n]/).map((x) => x.trim()).filter(Boolean);
function App() {
  const [tab, setTab] = useState("overview");
  const [menuOpen, setMenuOpen] = useState(false);
  const [profile, setProfile] = useState(INITIAL_PROFILE);
  const [key, setKey] = useState("");
  const [mode, setMode] = useState("ai");
  const [announcement, setAnnouncement] = useState("");
  const [manual, setManual] = useState({
    title: "", countries: "Nigeria", level: "", course: "", minCgpa: "",
    scale: "5", documents: "", officialUrl: "",
  });
  const [analysis, setAnalysis] = useState(null);
  const [checklist, setChecklist] = useState([]);
  const [completed, setCompleted] = useState([]);
  const [busy, setBusy] = useState(false);
  const [apiStatus, setApiStatus] = useState("checking");
  const [notice, setNotice] = useState("");
  const profileFields = ["country", "institution", "course_of_study", "academic_level", "cgpa"];
  const profileCount = profileFields.filter((field) => String(profile[field]).trim()).length;
  const profilePercent = Math.round(profileCount / profileFields.length * 100);
  const doneCount = checklist.filter((item) => completed.includes(item.id)).length;
  useEffect(() => {
    let active = true;
    fetch("/api/health")
      .then((res) => { if (!res.ok) throw new Error(); return res.json(); })
      .then((d) => { if (active) setApiStatus(d.status === "ok" ? "online" : "offline"); })
      .catch(() => { if (active) setApiStatus("offline"); });
    return () => { active = false; };
  }, []);
  const navigate = (next) => { setTab(next); setMenuOpen(false); window.scrollTo({ top: 0, behavior: "smooth" }); };
  const flash = (text) => { setNotice(text); };
  const change = (field, value) => setProfile((old) => ({ ...old, [field]: value }));
  const setCriterion = (field, value) => setManual((old) => ({ ...old, [field]: value }));
  const setNewAnalysis = async (opportunity, assessment, model) => {
    setAnalysis({ opportunity, assessment, model });
    setCompleted([]);
    try {
      const data = await apiPost("checklist", { opportunity });
      setChecklist(data.items || []);
    } catch { setChecklist([]); }
  };
  async function runAnalysis() {
    if (!profile.country.trim() || !profile.academic_level.trim()) {
      flash("Complete your country and academic level in My profile first.");
      navigate("profile");
      return;
    }
    setBusy(true);
    setNotice("");
    try {
      if (mode === "ai") {
        if (!key.trim()) throw new Error("Add your Google AI Studio key in Settings first.");
        if (announcement.trim().length < 100) throw new Error("Paste at least 100 characters from the official scholarship announcement.");
        const result = await apiPost("analyze", {
          profile: profileForApi(profile),
          announcement_text: announcement,
        }, key.trim());
        await setNewAnalysis(result.opportunity, result.assessment, result.model_used);
      } else {
        if (!manual.title.trim()) throw new Error("Enter the scholarship name.");
        const opportunity = {
          title: manual.title.trim(),
          eligible_countries: { countries: split(manual.countries), is_open_to_all: false },
          academic_level_requirements: manual.level ? [manual.level] : [],
          course_restrictions: split(manual.course),
          cgpa_requirement: {
            minimum: manual.minCgpa.trim() === "" ? null : Number(manual.minCgpa),
            scale: manual.minCgpa.trim() === "" ? null : Number(manual.scale),
          },
          required_documents: split(manual.documents).map((name) => ({ name, is_mandatory: true })),
          official_url: manual.officialUrl.trim() || null,
        };
        const assessment = await apiPost("assess", { profile: profileForApi(profile), opportunity });
        await setNewAnalysis(opportunity, assessment, "Rule-based assessment");
      }
      navigate("checklist");
      flash("Assessment completed. Review the eligibility results and your checklist.");
    } catch (err) {
      flash(err.message || "Could not analyze this opportunity.");
    } finally { setBusy(false); }
  }
  const profileCard = <div className="panel profile-progress">
    <div className="panel-kicker">PROFILE READINESS</div>
    <div className="progress-heading"><strong>{profilePercent}% complete</strong><span>{profileCount} of {profileFields.length} essentials</span></div>
    <div className="track"><div style={{ width: profilePercent + "%" }}/></div>
    <p>Add your academic details so eligibility checks can compare your qualifications.</p>
    <button className="text-button" onClick={() => navigate("profile")}>Complete your profile <ArrowRight size={15}/></button>
  </div>;
  return (
    <div className="app-shell">
      <aside className={"sidebar " + (menuOpen ? "show-sidebar" : "")}>
        <button className="brand" onClick={() => navigate("overview")} aria-label="Go to overview">
          <span className="brand-symbol"><GraduationCap size={24} strokeWidth={2.1}/></span>
          <span className="brand-text">Opportunity<span>Lens</span><small>YOUR FUTURE, IN FOCUS</small></span>
        </button>
        <div className="side-label">WORKSPACE</div>
        <nav aria-label="Main navigation">
          {MENU.map((item) => {
            const Icon = item.icon;
            return <button key={item.id} className={"nav-link " + (tab === item.id ? "nav-selected" : "")} onClick={() => navigate(item.id)}>
              <Icon size={19} strokeWidth={1.9}/><span>{item.name}</span>{tab === item.id && <ChevronRight size={16} className="nav-chevron"/>}
            </button>;
          })}
        </nav>
        <div className="side-bottom">
          <div className="side-tip"><Sparkles size={22}/><strong>Clarity before applying.</strong><p>Find the requirements, see where you stand, and prepare with confidence.</p></div>
          <div className="side-user"><span className="user-avatar"><UserCircle2 size={22}/></span><span><strong>Guest workspace</strong><small>Preview • not saved</small></span></div>
        </div>
      </aside>
      {menuOpen && <button className="mobile-shade" aria-label="Close navigation" onClick={() => setMenuOpen(false)}/>}
      <div className="body-shell">
        <header className="topbar">
          <div className="topbar-left"><button className="mobile-menu" onClick={() => setMenuOpen(true)} aria-label="Open menu"><Menu size={22}/></button><span className="crumb">WORKSPACE <span>/</span> <strong>{MENU.find((x) => x.id === tab)?.name}</strong></span></div>
          <div className="topbar-right"><span className="preview-pill"><span className="dot"/> PREVIEW</span><span className={"api-pill " + (apiStatus === "online" ? "healthy" : "")}>{apiStatus === "checking" ? "Checking API" : apiStatus === "online" ? "API connected" : "API unavailable"}</span><button className="user-button" aria-label="Open settings" onClick={() => navigate("settings")}><Settings size={17}/></button></div>
        </header>
        <main className="page-content">
          {notice && <div className="notice" role="status"><Info size={18}/><span>{notice}</span><button onClick={() => setNotice("")} aria-label="Dismiss message"><X size={17}/></button></div>}
          {tab === "overview" && <>
            <div className="dashboard-top"><span className="eyebrow">YOUR PERSONAL SCHOLARSHIP WORKSPACE</span><h1>Discover what's possible.<br/><em>Know where you stand.</em></h1><p>Turn scholarship requirements into clear answers and practical next steps, with the original OpportunityLens eligibility engine.</p><div className="hero-buttons"><button className="button button-white" onClick={() => navigate("analyze")}>Analyze an opportunity <ArrowRight size={17}/></button><button className="button button-outline-white" onClick={() => navigate("profile")}>Set up your profile</button></div><div className="hero-orb"><span className="orb-ring orb-first"/><span className="orb-ring orb-second"/><div className="orb-center"><Sparkles size={44}/></div><div className="floating-note note-one"><ShieldCheck size={17}/> Explainable results</div><div className="floating-note note-two"><FileCheck2 size={17}/> Application ready</div></div></div>
            <div className="stats-grid">
              <div className="stat-card"><span className="stat-icon blue"><UserCircle2 size={22}/></span><div><strong>{profilePercent}%</strong><p>Profile completion</p></div></div>
              <div className="stat-card"><span className="stat-icon violet"><FileSearch size={22}/></span><div><strong>{analysis ? "1" : "0"}</strong><p>Opportunities analyzed</p></div></div>
              <div className="stat-card"><span className="stat-icon green"><ClipboardCheck size={22}/></span><div><strong>{doneCount}/{checklist.length}</strong><p>Checklist items completed</p></div></div>
            </div>
            <div className="dashboard-columns">
              <section className="panel getting-started"><div className="section-head"><div><div className="panel-kicker">GETTING STARTED</div><h2>Three steps to your next opportunity</h2></div></div>
                {[{title:"Build your student profile",desc:"Add your institution, academic level, course and CGPA.",icon:UserCircle2,to:"profile",ready:profilePercent===100},
                  {title:"Understand scholarship requirements",desc:"Paste a real announcement or enter criteria yourself.",icon:FileSearch,to:"analyze",ready:!!analysis},
                  {title:"Prepare your application",desc:"Review evidence, missing information and required documents.",icon:ClipboardCheck,to:"checklist",ready:!!analysis&&checklist.length>0}].map((step,i)=>{
                  const Icon=step.icon;
                  return <button className="guide-step" key={step.title} onClick={() => navigate(step.to)}><span className={"guide-number " + (step.ready ? "step-ready" : "")}>{step.ready ? <Check size={16}/> : "0"+(i+1)}</span><span className="guide-content"><strong>{step.title}</strong><small>{step.desc}</small></span><ArrowUpRight size={18}/></button>;
                })}
              </section>
              <section className="panel aside-panel"><div className="panel-kicker">SMART MATCHING</div><span className="aside-spark"><WandSparkles size={24}/></span><h2>Not just a list of scholarships.</h2><p>OpportunityLens separates clear eligibility rules from requirements that still need human verification.</p><div className="feature-list"><span><CheckCircle2 size={17}/> Evidence-based eligibility checks</span><span><CheckCircle2 size={17}/> No invented CGPA conversions</span><span><CheckCircle2 size={17}/> Actionable preparation checklist</span></div><button className="text-button" onClick={() => navigate("analyze")}>Explore the analyzer <ArrowRight size={15}/></button></section>
            </div>
          </>}
          {tab === "discover" && <>
            <div className="page-header"><span className="eyebrow dark">OPPORTUNITY DISCOVERY</span><h1>Find your next opportunity</h1><p>Start with trusted official scholarship sources. Automated discovery and a searchable live feed are planned, not yet active.</p></div>
            <div className="panel message-panel"><div className="message-icon"><Compass size={24}/></div><div><strong>Your discovery feed is being built</strong><p>No scholarship listings have been invented or imported for this preview. Browse official providers below, then analyze an announcement you find.</p></div><button className="button button-primary" onClick={() => navigate("analyze")}>Analyze one <ArrowRight size={16}/></button></div>
            <div className="section-head extra-top"><div><span className="panel-kicker">OFFICIAL SOURCES</span><h2>Explore opportunities at the source</h2></div></div>
            <div className="source-grid">{SOURCES.map((source)=>{const Icon=source.icon;return <a className="source-card" key={source.url} href={source.url} target="_blank" rel="noopener noreferrer"><span className="source-icon"><Icon size={25}/></span><span className="source-body"><strong>{source.name}</strong><small>{source.desc}</small><span>Visit official website <ArrowUpRight size={15}/></span></span></a>})}</div>
            {analysis && <div className="panel previous-analysis"><span className="panel-kicker">THIS SESSION</span><h2>Your last analyzed opportunity</h2><div className="last-result"><span className="last-icon"><GraduationCap size={19}/></span><div><strong>{analysis.opportunity.title || "Untitled opportunity"}</strong><small>{formatStatus(analysis.assessment.overall_status)}</small></div><button className="button button-soft" onClick={() => navigate("checklist")}>Review <ArrowRight size={15}/></button></div></div>}
          </>}
          {tab === "profile" && <>
            <div className="page-header"><span className="eyebrow dark">PERSONALIZED ELIGIBILITY</span><h1>Your academic profile</h1><p>Provide accurate details to compare against scholarship eligibility rules. For this preview, information stays in this browser tab and is cleared when you reload.</p></div>
            <div className="profile-columns"><section className="panel profile-form"><div className="section-head"><div><span className="panel-kicker">BASIC INFORMATION</span><h2>About you</h2></div><span className="step-tag">Step 1 of 1</span></div>
              <div className="form-grid">
                <label className="field"><span>Full name <small>Optional</small></span><input placeholder="Your full name" value={profile.full_name} onChange={(e)=>change("full_name",e.target.value)} maxLength={100}/></label>
                <label className="field"><span>Country of citizenship</span><input placeholder="e.g. Nigeria" value={profile.country} onChange={(e)=>change("country",e.target.value)} maxLength={80}/></label>
                <label className="field full"><span>University or institution</span><input placeholder="e.g. Federal University Oye-Ekiti" value={profile.institution} onChange={(e)=>change("institution",e.target.value)} maxLength={140}/></label>
                <label className="field"><span>Course of study</span><input placeholder="e.g. Computer Engineering" value={profile.course_of_study} onChange={(e)=>change("course_of_study",e.target.value)} maxLength={120}/></label>
                <label className="field"><span>Academic level</span><select value={profile.academic_level} onChange={(e)=>change("academic_level",e.target.value)}><option value="">Select level</option>{LEVELS.map((level)=><option key={level} value={level}>{level}</option>)}</select></label>
                <label className="field"><span>Current CGPA</span><input type="number" min="0" max={profile.cgpa_scale || "5"} step="0.01" placeholder="e.g. 4.50" value={profile.cgpa} onChange={(e)=>change("cgpa",e.target.value)}/></label>
                <label className="field"><span>Grading scale</span><select value={profile.cgpa_scale} onChange={(e)=>change("cgpa_scale",e.target.value)}><option value="5">5.0</option><option value="4">4.0</option><option value="7">7.0</option></select></label>
                <label className="field"><span>Age <small>Optional</small></span><input type="number" min="1" max="120" placeholder="Your age" value={profile.age} onChange={(e)=>change("age",e.target.value)}/></label>
              </div>
              <div className="form-actions"><span><LockKeyhole size={15}/> Not synced to a server</span><button className="button button-primary" onClick={()=> {if(profile.cgpa && (Number(profile.cgpa)<0 || Number(profile.cgpa)>Number(profile.cgpa_scale))){flash("Your CGPA must be within your selected grading scale.");return;}navigate("analyze");}}>Continue to analyzer <ArrowRight size={16}/></button></div>
            </section><div className="side-stack">{profileCard}<div className="panel small-note"><ShieldCheck size={22}/><h3>Transparent matching</h3><p>Your information is evaluated by clear Python rules. Different CGPA grading scales require verification, not guessed conversions.</p></div></div></div>
          </>}
          {tab === "analyze" && <>
            <div className="page-header"><span className="eyebrow dark">AI + TRANSPARENT RULES</span><h1>Scholarship eligibility analyzer</h1><p>Understand whether an opportunity matches your academic profile before investing time in the application.</p></div>
            <div className="analyze-columns"><section className="panel analysis-panel"><div className="section-head"><div><span className="panel-kicker">CHOOSE YOUR METHOD</span><h2>Analyze an opportunity</h2></div><div className="method-tabs"><button className={mode==="ai"?"active":""} onClick={()=>setMode("ai")}><Sparkles size={15}/> With AI</button><button className={mode==="manual"?"active":""} onClick={()=>setMode("manual")}><ClipboardCheck size={15}/> Manual</button></div></div>
              {mode==="ai"?<><div className="instruction-box"><WandSparkles size={18}/><span>Copy the full text of an official scholarship announcement. Gemma extracts structured criteria, then the Python rules assess your profile.</span></div><label className="field full"><span>Scholarship announcement</span><textarea rows="11" value={announcement} onChange={(e)=>setAnnouncement(e.target.value)} placeholder="Paste the official scholarship announcement, including eligibility criteria, documents, application deadline and source link..." maxLength={100000}/></label><div className="hint"><KeyRound size={16}/> Requires your own Google AI Studio API key. <button onClick={()=>navigate("settings")}>Configure key</button></div></>:<><div className="instruction-box"><ShieldCheck size={18}/><span>No AI key needed. Enter only the eligibility requirements stated by the scholarship provider.</span></div><div className="form-grid"><label className="field full"><span>Opportunity title</span><input placeholder="Official scholarship name" value={manual.title} onChange={(e)=>setCriterion("title",e.target.value)}/></label><label className="field"><span>Eligible countries</span><input value={manual.countries} onChange={(e)=>setCriterion("countries",e.target.value)} placeholder="Nigeria, Ghana"/></label><label className="field"><span>Academic level required</span><select value={manual.level} onChange={(e)=>setCriterion("level",e.target.value)}><option value="">Not specified</option>{LEVELS.map((l)=><option key={l}>{l}</option>)}</select></label><label className="field full"><span>Eligible courses <small>Separate with commas</small></span><input value={manual.course} onChange={(e)=>setCriterion("course",e.target.value)} placeholder="e.g. Engineering, Computer Science"/></label><label className="field"><span>Minimum CGPA</span><input type="number" min="0" step="0.01" value={manual.minCgpa} onChange={(e)=>setCriterion("minCgpa",e.target.value)} placeholder="If specified"/></label><label className="field"><span>Required CGPA scale</span><select value={manual.scale} onChange={(e)=>setCriterion("scale",e.target.value)}><option value="5">5.0</option><option value="4">4.0</option><option value="7">7.0</option></select></label><label className="field full"><span>Required documents <small>Separate with commas</small></span><input value={manual.documents} onChange={(e)=>setCriterion("documents",e.target.value)} placeholder="e.g. Transcript, Recommendation letter"/></label><label className="field full"><span>Official application URL <small>Optional</small></span><input type="url" value={manual.officialUrl} onChange={(e)=>setCriterion("officialUrl",e.target.value)} placeholder="https://..."/></label></div></>}
              <div className="form-actions"><span><ShieldCheck size={16}/> Evidence matters. Always verify official requirements.</span><button className="button button-primary" onClick={runAnalysis} disabled={busy}>{busy?"Analyzing...":"Check my eligibility"} {!busy&&<ArrowRight size={16}/>}</button></div>
            </section><div className="side-stack">{profileCard}<div className="panel small-note"><Info size={22}/><h3>What your result means</h3><p>“Likely eligible” means the identified rules match, not that an award is guaranteed. Missing or ambiguous requirements are flagged for review.</p></div></div></div>
          </>}
          {tab === "checklist" && <>
            <div className="page-header"><span className="eyebrow dark">APPLICATION READINESS</span><h1>Your application roadmap</h1><p>Move from eligibility findings to clear steps for preparing an application.</p></div>
            {!analysis?<div className="panel empty-state"><span className="empty-icon"><ClipboardCheck size={32}/></span><h2>No application checklist yet</h2><p>Analyze a real scholarship announcement or enter its criteria manually to generate a personalized starting checklist.</p><button className="button button-primary" onClick={()=>navigate("analyze")}>Analyze a scholarship <ArrowRight size={17}/></button></div>:<>
              <div className="result-heading"><div><span className="panel-kicker">YOUR LATEST ASSESSMENT</span><h2>{analysis.opportunity.title || "Opportunity analysis"}</h2><p>{analysis.opportunity.organizing_institution || "Scholarship eligibility evaluation"}</p></div><span className={"status-badge "+analysis.assessment.overall_status.toLowerCase()}>{formatStatus(analysis.assessment.overall_status)}</span></div>
              <div className="assessment-grid"><section className="panel"><div className="section-head"><div><span className="panel-kicker">TRANSPARENT RESULTS</span><h2>Eligibility breakdown</h2></div><span className="mini-pill">{analysis.assessment.met_count} met · {analysis.assessment.needs_verification_count} verify</span></div>
                <p className="assessment-explanation">{analysis.assessment.overall_explanation}</p>
                <div className="criteria">{analysis.assessment.requirement_checks.map((check,i)=><div className="criterion" key={i}><span className={"criterion-dot "+check.status.toLowerCase()}>{check.status==="MET"?<Check size={15}/>:check.status==="NOT_MET"?<X size={15}/>:<Info size={15}/>}</span><div><strong>{check.requirement}</strong><p>{check.explanation}</p>{check.source_excerpt&&<small>Source: {check.source_excerpt}</small>}</div><span className={"check-status "+check.status.toLowerCase()}>{formatStatus(check.status)}</span></div>)}</div>
              </section><section className="panel"><div className="section-head"><div><span className="panel-kicker">PREPARE TO APPLY</span><h2>Application checklist</h2></div><span className="mini-pill">{doneCount}/{checklist.length} complete</span></div><div className="track"><div style={{width:(checklist.length?Math.round(doneCount/checklist.length*100):0)+"%"}}/></div>{checklist.length===0?<div className="blank-checklist">No specific documents or actions were found. Review the official announcement.</div>:checklist.map((item)=><label className={"checklist-row "+(completed.includes(item.id)?"checked":"")} key={item.id}><input type="checkbox" checked={completed.includes(item.id)} onChange={()=>setCompleted((old)=>old.includes(item.id)?old.filter((x)=>x!==item.id):[...old,item.id])}/><span><strong>{item.description}</strong><small>{item.detail}</small></span></label>)}<div className="disclaimer"><ShieldCheck size={17}/><span>{analysis.assessment.disclaimer}</span></div>{analysis.opportunity.official_url&&<a className="button button-primary full-button" href={analysis.opportunity.official_url} target="_blank" rel="noopener noreferrer">Official application page <ExternalLink size={16}/></a>}</section></div>
            </>}
          </>}
          {tab === "settings" && <>
            <div className="page-header"><span className="eyebrow dark">PREFERENCES & PRIVACY</span><h1>Workspace settings</h1><p>Control how this preview uses AI and handles your information.</p></div>
            <div className="settings-grid"><div className="panel settings-panel"><div className="settings-section"><span className="settings-icon"><KeyRound size={21}/></span><div><h2>Your Google AI Studio key</h2><p>Bring your own API key to extract requirements from scholarship announcements.</p></div></div><label className="field full"><span>Gemma API key <small>Session-only</small></span><input type="password" value={key} onChange={(e)=>setKey(e.target.value)} autoComplete="off" placeholder="Paste your API key here"/></label><div className="form-actions"><p>Never share API keys. Your key is held in memory and sent only when you run an analysis. It is not written to localStorage or the database.</p><button className="button button-soft" onClick={()=>{setKey("");flash("API key cleared from this page.");}}>Clear key</button></div><a className="text-link" target="_blank" rel="noopener noreferrer" href="https://aistudio.google.com/apikey">Get an API key from Google AI Studio <ExternalLink size={14}/></a></div>
              <div className="panel settings-panel"><div className="settings-section"><span className="settings-icon"><ShieldCheck size={21}/></span><div><h2>Guest preview</h2><p>This version doesn't offer accounts or cloud profile storage yet.</p></div></div><div className="privacy-list"><p><CheckCircle2 size={17}/> Profile stays in memory in this browser tab.</p><p><CheckCircle2 size={17}/> No scholarship application is submitted automatically.</p><p><CheckCircle2 size={17}/> Only supplied announcements are analyzed.</p><p><Clock3 size={17}/> Email alerts and live discovery are planned.</p></div><button className="button button-outline" onClick={()=>{setProfile(INITIAL_PROFILE);setAnalysis(null);setChecklist([]);setCompleted([]);setKey("");setAnnouncement("");flash("Your in-memory preview data has been cleared.");navigate("overview");}}>Clear guest workspace</button></div></div>
          </>}
        </main>
        <footer className="footer"><span>OpportunityLens · Open-source scholarship clarity</span><span>Early web preview · Built on the existing Python eligibility engine</span></footer>
      </div>
    </div>
  );
}
createRoot(document.getElementById("root")).render(<App/>);
