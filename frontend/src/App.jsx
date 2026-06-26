import React, { useState, useEffect, useRef } from "react";
import Chart from "chart.js/auto";

// Determine API Base URL dynamically
const API_BASE = window.location.port === "5173" ? "http://127.0.0.1:8000" : "";

export default function App() {
  // Navigation & View States
  const [currentView, setCurrentView] = useState("survey"); // "survey" | "admin"
  const [evaluatorInfo, setEvaluatorInfo] = useState(null);
  const [surveyConfig, setSurveyConfig] = useState(null);
  const [surveyStep, setSurveyStep] = useState(0); // 0: Onboarding, 1->N: TTS, N+1->M: Audio, M+1: Submit
  
  // Survey responses state
  const [responses, setResponses] = useState({
    tts: {}, // key: "ttsId_voice", value: { naturalness, pronunciation, intonation, overall }
    stt: {}, // key: "audioId_filename", value: { clarity, intelligibility, noise, overall }
    comments: ""
  });

  // Admin Dashboard States
  const [dashboardData, setDashboardData] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Custom Transcribe tool states
  const [transcribeFile, setTranscribeFile] = useState(null);
  const [transcribeModel, setTranscribeModel] = useState("base");
  const [transcribeLanguage, setTranscribeLanguage] = useState("");
  const [transcribeResult, setTranscribeResult] = useState(null);
  const [isTranscribing, setIsTranscribing] = useState(false);

  // Unified Pipeline tool states
  const [pipelineFile, setPipelineFile] = useState(null);
  const [pipelineVoice, setPipelineVoice] = useState("amy");
  const [pipelineFormat, setPipelineFormat] = useState("wav");
  const [pipelineResult, setPipelineResult] = useState(null);
  const [isProcessingPipeline, setIsProcessingPipeline] = useState(false);

  // Chart Canvas Refs
  const ttsChartCanvasRef = useRef(null);
  const sttChartCanvasRef = useRef(null);
  const ttsChartRef = useRef(null);
  const sttChartRef = useRef(null);

  // Onboarding input states
  const [onboardName, setOnboardName] = useState("");
  const [onboardAge, setOnboardAge] = useState("25-34");
  const [onboardNoise, setOnboardNoise] = useState("quiet");

  // Load dashboard data when view changes
  useEffect(() => {
    if (currentView === "admin") {
      fetchDashboardData();
    }
  }, [currentView]);

  // Clean charts on unmount or refresh
  useEffect(() => {
    return () => {
      if (ttsChartRef.current) ttsChartRef.current.destroy();
      if (sttChartRef.current) sttChartRef.current.destroy();
    };
  }, []);

  // Redraw charts when dashboard data loads
  useEffect(() => {
    if (currentView === "admin" && dashboardData) {
      drawTtsChart();
      drawSttChart();
    }
  }, [dashboardData, currentView]);

  // Fetch survey configuration from FastAPI
  const handleOnboardingSubmit = async (e) => {
    e.preventDefault();
    if (!onboardName.trim()) {
      alert("Please enter your name or identifier to start.");
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/api/survey-config`);
      if (!res.ok) throw new Error("Survey configuration not found on backend.");
      const data = await res.json();
      setSurveyConfig(data);
      setEvaluatorInfo({ name: onboardName.trim(), age: onboardAge, noise: onboardNoise });
      setSurveyStep(1);
    } catch (err) {
      console.error(err);
      alert("Error loading survey data. Please verify that python tests/prepare_survey_data.py has been run and the backend server is running.");
    }
  };

  // Fetch results from backend
  const fetchDashboardData = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/results`);
      if (!res.ok) throw new Error("Failed to load dashboard data.");
      const data = await res.json();
      setDashboardData(data);
    } catch (err) {
      console.error(err);
    }
  };

  // Submit survey responses
  const handleSubmitSurvey = async () => {
    const ttsResponses = Object.keys(responses.tts).map(key => {
      const [id, voice] = key.split("_");
      return { id, voice, ...responses.tts[key] };
    });

    const sttResponses = Object.keys(responses.stt).map(key => {
      const [id, filename] = key.split("_");
      return { id, filename, ...responses.stt[key] };
    });

    const payload = {
      userInfo: evaluatorInfo,
      ttsResponses,
      sttResponses,
      comments: responses.comments
    };

    try {
      setIsSubmitting(true);
      const res = await fetch(`${API_BASE}/api/submit-survey`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error("Failed to save survey results.");
      
      alert("Survey successfully submitted! Thank you.");
      
      // Reset survey state
      setEvaluatorInfo(null);
      setResponses({ tts: {}, stt: {}, comments: "" });
      setOnboardName("");
      setSurveyStep(0);
      setCurrentView("admin");
    } catch (err) {
      console.error(err);
      alert("Error submitting survey. Please check your backend connection and try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Submit custom audio file for transcription
  const handleTranscribeSubmit = async (e) => {
    e.preventDefault();
    if (!transcribeFile) {
      alert("Please select or drop an audio file to transcribe.");
      return;
    }

    const formData = new FormData();
    formData.append("file", transcribeFile);
    if (transcribeModel) {
      formData.append("model", transcribeModel);
    }
    if (transcribeLanguage) {
      formData.append("language", transcribeLanguage);
    }

    try {
      setIsTranscribing(true);
      setTranscribeResult(null);
      
      const res = await fetch(`${API_BASE}/api/v1/stt`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Transcription failed.");
      }

      const data = await res.json();
      setTranscribeResult(data);
    } catch (err) {
      console.error(err);
      alert("Error: " + err.message);
    } finally {
      setIsTranscribing(false);
    }
  };

  // Submit custom audio file for unified STT-NLU-TTS processing
  const handlePipelineSubmit = async (e) => {
    e.preventDefault();
    if (!pipelineFile) {
      alert("Please select or drop an audio file to process.");
      return;
    }

    const formData = new FormData();
    formData.append("file", pipelineFile);
    formData.append("tts_voice", pipelineVoice);
    formData.append("tts_format", pipelineFormat);

    try {
      setIsProcessingPipeline(true);
      setPipelineResult(null);
      
      const res = await fetch(`${API_BASE}/api/v1/process`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Pipeline processing failed.");
      }

      const data = await res.json();
      setPipelineResult(data);
    } catch (err) {
      console.error(err);
      alert("Error: " + err.message);
    } finally {
      setIsProcessingPipeline(false);
    }
  };

  // Navigation handlers
  const ttsTasksCount = surveyConfig?.tts?.length || 0;
  const sttTasksCount = surveyConfig?.stt?.length || 0;
  const totalSurveySteps = ttsTasksCount + sttTasksCount + 1; // +1 for comment page

  const handleTtsNext = (task) => {
    let incomplete = false;
    for (const voiceEval of task.voice_evals) {
      const responseKey = `${task.id}_${voiceEval.voice}`;
      const score = responses.tts[responseKey];
      if (!score || !score.naturalness || !score.pronunciation || !score.intonation || !score.overall) {
        incomplete = true;
        break;
      }
    }
    if (incomplete) {
      alert("Please rate all parameters (1-5 stars) for every voice model on this page before proceeding.");
      return;
    }
    setSurveyStep(prev => prev + 1);
  };

  const handleSttNext = (task) => {
    const responseKey = `${task.id}_${task.filename}`;
    const score = responses.stt[responseKey];
    const incomplete = !score || !score.clarity || !score.intelligibility || !score.noise || !score.overall;
    
    if (incomplete) {
      alert("Please rate all parameters (1-5 stars) for this audio clip before proceeding.");
      return;
    }
    setSurveyStep(prev => prev + 1);
  };

  // Interactive rating updates
  const setStarRating = (type, key, category, value) => {
    setResponses(prev => {
      const nextResponses = { ...prev };
      if (type === "tts") {
        if (!nextResponses.tts[key]) {
          nextResponses.tts[key] = { naturalness: 0, pronunciation: 0, intonation: 0, overall: 0 };
        }
        nextResponses.tts[key][category] = value;
      } else {
        if (!nextResponses.stt[key]) {
          nextResponses.stt[key] = { clarity: 0, intelligibility: 0, noise: 0, overall: 0 };
        }
        nextResponses.stt[key][category] = value;
      }
      return nextResponses;
    });
  };

  // Star Widget Component
  const StarRating = ({ type, responseKey, category, value }) => {
    const [hoverValue, setHoverValue] = useState(0);
    return (
      <div className="stars-container">
        {[1, 2, 3, 4, 5].map(starIdx => {
          const isSelected = starIdx <= value;
          const isGlowing = starIdx <= hoverValue;
          return (
            <button
              key={starIdx}
              type="button"
              className={`star-btn ${isSelected ? "selected" : ""} ${isGlowing ? "glow" : ""}`}
              onMouseEnter={() => setHoverValue(starIdx)}
              onMouseLeave={() => setHoverValue(0)}
              onClick={() => setStarRating(type, responseKey, category, starIdx)}
            >
              <i className="fa-solid fa-star"></i>
            </button>
          );
        })}
      </div>
    );
  };

  // Rendering Helper for Star Ratings Item
  const RatingItem = ({ type, responseKey, category, label, value }) => (
    <div className="rating-item">
      <span>{label}</span>
      <StarRating type={type} responseKey={responseKey} category={category} value={value} />
    </div>
  );

  // Drawing Charts
  const drawTtsChart = () => {
    if (!ttsChartCanvasRef.current || !dashboardData) return;
    if (ttsChartRef.current) ttsChartRef.current.destroy();

    const ttsData = dashboardData.summary.tts;
    const voices = Object.keys(ttsData);
    if (voices.length === 0) return;

    const categories = ["naturalness", "pronunciation", "intonation", "overall"];
    const categoryLabels = ["Naturalness", "Pronunciation", "Intonation", "Overall Quality"];
    const colors = ["#6366f1", "#3b82f6", "#a855f7", "#ec4899"];

    const datasets = categories.map((cat, idx) => ({
      label: categoryLabels[idx],
      data: voices.map(voice => ttsData[voice][cat].mean),
      backgroundColor: colors[idx],
      borderRadius: 4
    }));

    ttsChartRef.current = new Chart(ttsChartCanvasRef.current.getContext("2d"), {
      type: "bar",
      data: { labels: voices, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: { min: 1, max: 5, grid: { color: "rgba(255,255,255,0.05)" }, ticks: { color: "#a1a1aa" } },
          x: { grid: { display: false }, ticks: { color: "#a1a1aa" } }
        },
        plugins: {
          legend: { labels: { color: "#f3f4f6" } }
        }
      }
    });
  };

  const drawSttChart = () => {
    if (!sttChartCanvasRef.current || !dashboardData) return;
    if (sttChartRef.current) sttChartRef.current.destroy();

    const sttData = dashboardData.summary.stt;
    const files = Object.keys(sttData);
    if (files.length === 0) return;

    const categories = ["clarity", "intelligibility", "noise", "overall"];
    const categoryLabels = ["Clarity", "Intelligibility", "Noise Control", "Overall Quality"];
    const colors = ["#10b981", "#3b82f6", "#fbbf24", "#ef4444"];

    const datasets = categories.map((cat, idx) => ({
      label: categoryLabels[idx],
      data: files.map(file => sttData[file][cat].mean),
      backgroundColor: colors[idx],
      borderRadius: 4
    }));

    sttChartRef.current = new Chart(sttChartCanvasRef.current.getContext("2d"), {
      type: "bar",
      data: { labels: files, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: { min: 1, max: 5, grid: { color: "rgba(255,255,255,0.05)" }, ticks: { color: "#a1a1aa" } },
          x: { grid: { display: false }, ticks: { color: "#a1a1aa" } }
        },
        plugins: {
          legend: { labels: { color: "#f3f4f6" } }
        }
      }
    });
  };

  // CSV Generator Link
  const getCsvDownloadHref = () => {
    if (!dashboardData || dashboardData.raw_responses.length === 0) return "#";
    let csv = "Evaluator,Age,Noise,EvaluationType,Model/Voice,Metric,Score\n";
    
    dashboardData.raw_responses.forEach(r => {
      const evalName = r.userInfo.name.replace(/,/g, " ");
      const age = r.userInfo.age;
      const noise = r.userInfo.noise;

      r.ttsResponses.forEach(item => {
        const voice = item.voice.replace(/,/g, " ");
        csv += `${evalName},${age},${noise},TTS,${voice},Naturalness,${item.naturalness}\n`;
        csv += `${evalName},${age},${noise},TTS,${voice},Pronunciation,${item.pronunciation}\n`;
        csv += `${evalName},${age},${noise},TTS,${voice},Intonation,${item.intonation}\n`;
        csv += `${evalName},${age},${noise},TTS,${voice},Overall,${item.overall}\n`;
      });

      r.sttResponses.forEach(item => {
        const filename = item.filename.replace(/,/g, " ");
        csv += `${evalName},${age},${noise},AudioQuality,${filename},Clarity,${item.clarity}\n`;
        csv += `${evalName},${age},${noise},AudioQuality,${filename},Intelligibility,${item.intelligibility}\n`;
        csv += `${evalName},${age},${noise},AudioQuality,${filename},Noise,${item.noise}\n`;
        csv += `${evalName},${age},${noise},AudioQuality,${filename},Overall,${item.overall}\n`;
      });
    });

    return "data:text/csv;charset=utf-8," + encodeURIComponent(csv);
  };

  // Top Metrics Calculation for Display Cards
  const getTopTtsVoice = () => {
    if (!dashboardData) return "N/A";
    let topName = "N/A";
    let topScore = 0;
    Object.keys(dashboardData.summary.tts).forEach(voice => {
      const mean = dashboardData.summary.tts[voice].overall.mean;
      if (mean > topScore) {
        topScore = mean;
        topName = voice.split(" ")[0];
      }
    });
    return topName === "N/A" ? "N/A" : `${topName} (${topScore.toFixed(1)})`;
  };

  const getTopAudioQuality = () => {
    if (!dashboardData) return "N/A";
    let topName = "N/A";
    let topScore = 0;
    Object.keys(dashboardData.summary.stt).forEach(file => {
      const mean = dashboardData.summary.stt[file].overall.mean;
      if (mean > topScore) {
        topScore = mean;
        topName = file;
      }
    });
    return topName === "N/A" ? "N/A" : `${topName} (${topScore.toFixed(1)})`;
  };

  // Details Table Data Gathering
  const getDetailsTableRows = () => {
    if (!dashboardData) return [];
    const rows = [];
    Object.keys(dashboardData.summary.tts).forEach(voice => {
      const stats = dashboardData.summary.tts[voice].overall;
      rows.push({ name: voice, category: "Text-to-Speech", ...stats });
    });
    Object.keys(dashboardData.summary.stt).forEach(file => {
      const stats = dashboardData.summary.stt[file].overall;
      rows.push({ name: file, category: "Audio Quality", ...stats });
    });
    return rows.sort((a, b) => {
      if (a.category !== b.category) return a.category.localeCompare(b.category);
      return b.mean - a.mean;
    });
  };

  // Render view controller
  return (
    <>
      <div className="glass-bg-decor decor1"></div>
      <div className="glass-bg-decor decor2"></div>

      <header className="app-header">
        <div className="logo-area">
          <i className="fa-solid fa-microphone-lines brand-icon"></i>
          <div>
            <h1>Audio Evaluation Hub</h1>
            <p className="subtitle">Speech Benchmarks Dashboard (React + FastAPI)</p>
          </div>
        </div>
        <nav className="app-nav">
          <button 
            className={`nav-btn ${currentView === "survey" ? "active" : ""}`} 
            onClick={() => setCurrentView("survey")}
          >
            <i className="fa-solid fa-list-check"></i> Take Survey
          </button>
          <button 
            className={`nav-btn ${currentView === "transcribe" ? "active" : ""}`} 
            onClick={() => setCurrentView("transcribe")}
          >
            <i className="fa-solid fa-file-audio"></i> Transcribe Audio
          </button>
          <button 
            className={`nav-btn ${currentView === "pipeline" ? "active" : ""}`} 
            onClick={() => setCurrentView("pipeline")}
          >
            <i className="fa-solid fa-arrows-spin"></i> Unified Pipeline
          </button>
          <button 
            className={`nav-btn ${currentView === "admin" ? "active" : ""}`} 
            onClick={() => setCurrentView("admin")}
          >
            <i className="fa-solid fa-chart-simple"></i> Analytics Dashboard
          </button>
        </nav>
      </header>

      <main className="main-content">
        
        {currentView === "survey" && (
          <section id="survey-section" className="app-view active">
            
            {/* ONBOARDING STEP */}
            {surveyStep === 0 && (
              <div id="onboarding-card" className="card fade-in">
                <div className="card-header gradient-1">
                  <h2><i className="fa-solid fa-user-astronaut"></i> Evaluator Onboarding</h2>
                  <p>Please enter your information to begin the speech evaluation session.</p>
                </div>
                <div class="card-body">
                  <form onSubmit={handleOnboardingSubmit}>
                    <div className="form-group">
                      <label htmlFor="evaluator-name">Full Name / Identifier <span className="required">*</span></label>
                      <input 
                        type="text" 
                        id="evaluator-name" 
                        placeholder="e.g. User 1 or John Doe" 
                        required 
                        value={onboardName}
                        onChange={(e) => setOnboardName(e.target.value)}
                      />
                    </div>
                    
                    <div className="form-row">
                      <div className="form-group">
                        <label htmlFor="evaluator-age">Age Group</label>
                        <select 
                          id="evaluator-age" 
                          value={onboardAge} 
                          onChange={(e) => setOnboardAge(e.target.value)}
                        >
                          <option value="18-24">18 - 24 years</option>
                          <option value="25-34">25 - 34 years</option>
                          <option value="35-44">35 - 44 years</option>
                          <option value="45-54">45 - 54 years</option>
                          <option value="55+">55+ years</option>
                        </select>
                      </div>
                      <div className="form-group">
                        <label htmlFor="evaluator-noise">Background Noise Level</label>
                        <select 
                          id="evaluator-noise" 
                          value={onboardNoise} 
                          onChange={(e) => setOnboardNoise(e.target.value)}
                        >
                          <option value="quiet">Quiet Room (Recommended)</option>
                          <option value="moderate">Moderate Noise (e.g. Office)</option>
                          <option value="noisy">Loud Environment (e.g. Cafe/Street)</option>
                        </select>
                      </div>
                    </div>
                    
                    <div className="info-alert">
                      <i className="fa-solid fa-circle-info"></i>
                      <p>For best results, please complete this survey using <strong>headphones</strong> in a quiet environment. This survey takes approximately 10 minutes.</p>
                    </div>
                    
                    <button type="submit" className="btn btn-primary btn-block">
                      Start Evaluation <i className="fa-solid fa-chevron-right"></i>
                    </button>
                  </form>
                </div>
              </div>
            )}

            {/* SURVEY CORE STEPS */}
            {surveyStep > 0 && (
              <div id="survey-core" className="fade-in">
                
                {/* Progress Tracker */}
                <div className="progress-container">
                  <div className="progress-bar-wrapper">
                    <div 
                      className="progress-bar" 
                      style={{ width: `${((surveyStep - 1) / totalSurveySteps) * 100}%` }}
                    ></div>
                  </div>
                  <div className="progress-meta">
                    <span>
                      {surveyStep === totalSurveySteps 
                        ? "Final Step: Submission" 
                        : `Evaluation Task ${surveyStep} of ${totalSurveySteps - 1}`}
                    </span>
                    <span>{Math.round(((surveyStep - 1) / totalSurveySteps) * 100)}% Completed</span>
                  </div>
                </div>

                {/* Part 1: TTS Phrase Evaluation */}
                {surveyStep <= ttsTasksCount && (
                  <div id="tts-eval-card" className="card fade-in">
                    <div className="card-header gradient-2">
                      <span className="badge">Part 1: Text-to-Speech Quality (MOS)</span>
                      <h2>TTS Phrase Evaluation</h2>
                      <p>Listen to the generated voice clips of the phrase below, and score each voice model.</p>
                    </div>
                    <div className="card-body">
                      <div className="reference-phrase-box">
                        <span className="label">Reference Phrasing:</span>
                        <blockquote>"{surveyConfig.tts[surveyStep - 1].text}"</blockquote>
                      </div>

                      <div className="voices-rating-container">
                        {surveyConfig.tts[surveyStep - 1].voice_evals.map(voiceEval => {
                          const voiceName = voiceEval.voice;
                          const key = `${surveyConfig.tts[surveyStep - 1].id}_${voiceName}`;
                          const saved = responses.tts[key] || { naturalness: 0, pronunciation: 0, intonation: 0, overall: 0 };
                          
                          return (
                            <div className="voice-row fade-in" key={voiceName}>
                              <div className="row-header">
                                <h4><i className="fa-solid fa-volume-high"></i> Voice Model: {voiceName}</h4>
                                <audio controls src={API_BASE + voiceEval.audio_path}></audio>
                              </div>
                              <div className="ratings-grid">
                                <RatingItem 
                                  type="tts" responseKey={key} category="naturalness" 
                                  label="Naturalness" value={saved.naturalness} 
                                />
                                <RatingItem 
                                  type="tts" responseKey={key} category="pronunciation" 
                                  label="Pronunciation" value={saved.pronunciation} 
                                />
                                <RatingItem 
                                  type="tts" responseKey={key} category="intonation" 
                                  label="Intonation & Cadence" value={saved.intonation} 
                                />
                                <RatingItem 
                                  type="tts" responseKey={key} category="overall" 
                                  label="Overall Voice Quality" value={saved.overall} 
                                />
                              </div>
                            </div>
                          );
                        })}
                      </div>

                      <div className="nav-actions">
                        <button className="btn btn-secondary" onClick={() => setSurveyStep(prev => prev - 1)}>
                          <i className="fa-solid fa-chevron-left"></i> Previous
                        </button>
                        <button 
                          className="btn btn-primary" 
                          onClick={() => handleTtsNext(surveyConfig.tts[surveyStep - 1])}
                        >
                          Next Phrase <i className="fa-solid fa-chevron-right"></i>
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {/* Part 2: Reference Audio Quality Evaluation */}
                {surveyStep > ttsTasksCount && surveyStep < totalSurveySteps && (() => {
                  const taskIndex = surveyStep - ttsTasksCount - 1;
                  const task = surveyConfig.stt[taskIndex];
                  const key = `${task.id}_${task.filename}`;
                  const saved = responses.stt[key] || { clarity: 0, intelligibility: 0, noise: 0, overall: 0 };
                  
                  return (
                    <div id="stt-eval-card" className="card fade-in">
                      <div className="card-header gradient-3">
                        <span className="badge">Part 2: Reference Audio Quality (MOS)</span>
                        <h2>Audio Quality Evaluation</h2>
                        <p>Listen to the spoken audio and score its overall clarity, intelligibility, and background noise level.</p>
                      </div>
                      <div className="card-body">
                        <div className="audio-source-box">
                          <span className="label">Spoken Reference Audio:</span>
                          <div className="custom-player-wrapper">
                            <audio controls src={API_BASE + task.audio_path} className="full-audio"></audio>
                          </div>
                          {task.reference_text && (
                            <div className="ref-transcript-collapsed">
                              <details>
                                <summary>Reveal Reference Transcript (Ground Truth)</summary>
                                <p>{task.reference_text}</p>
                              </details>
                            </div>
                          )}
                        </div>

                        <div className="models-rating-container">
                          <div className="model-row fade-in">
                            <div className="row-header">
                              <h4><i className="fa-solid fa-file-audio"></i> Audio Clip: {task.filename}</h4>
                            </div>
                            <div className="ratings-grid">
                              <RatingItem 
                                type="stt" responseKey={key} category="clarity" 
                                label="Speech Clarity" value={saved.clarity} 
                              />
                              <RatingItem 
                                type="stt" responseKey={key} category="intelligibility" 
                                label="Word Intelligibility" value={saved.intelligibility} 
                              />
                              <RatingItem 
                                type="stt" responseKey={key} category="noise" 
                                label="Background Noise Control" value={saved.noise} 
                              />
                              <RatingItem 
                                type="stt" responseKey={key} category="overall" 
                                label="Overall Audio Quality" value={saved.overall} 
                              />
                            </div>
                          </div>
                        </div>

                        <div className="nav-actions">
                          <button className="btn btn-secondary" onClick={() => setSurveyStep(prev => prev - 1)}>
                            <i className="fa-solid fa-chevron-left"></i> Previous
                          </button>
                          <button className="btn btn-primary" onClick={() => handleSttNext(task)}>
                            Next Audio <i className="fa-solid fa-chevron-right"></i>
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })()}

                {/* Final step: Submit survey responses */}
                {surveyStep === totalSurveySteps && (
                  <div id="submit-card" class="card fade-in">
                    <div className="card-header gradient-1">
                      <h2><i className="fa-solid fa-check-double"></i> Complete & Submit</h2>
                      <p>Thank you! You have finished evaluating all sample sets. Please provide any overall comments.</p>
                    </div>
                    <div className="card-body">
                      <div className="form-group">
                        <label htmlFor="survey-comments">General Feedback / Comments (Optional)</label>
                        <textarea 
                          id="survey-comments" 
                          rows="4" 
                          placeholder="Mention any audio issues, specific speech patterns, or thoughts on model comparison..."
                          value={responses.comments}
                          onChange={(e) => setResponses(prev => ({ ...prev, comments: e.target.value }))}
                        ></textarea>
                      </div>

                      <div className="nav-actions">
                        <button className="btn btn-secondary" onClick={() => setSurveyStep(prev => prev - 1)}>
                          <i className="fa-solid fa-chevron-left"></i> Previous
                        </button>
                        <button 
                          id="submit-survey-btn" 
                          className="btn btn-success" 
                          onClick={handleSubmitSurvey}
                          disabled={isSubmitting}
                        >
                          {isSubmitting ? "Submitting..." : "Submit Survey"} <i className="fa-solid fa-paper-plane"></i>
                        </button>
                      </div>
                    </div>
                  </div>
                )}

              </div>
            )}

          </section>
        )}

        {currentView === "admin" && (
          <section id="admin-section" className="app-view active fade-in">
            
            <div className="dashboard-header-row">
              <h2><i className="fa-solid fa-chart-line"></i> Speech Quality Analysis</h2>
              <div className="dash-actions">
                <button className="btn btn-secondary btn-sm" onClick={fetchDashboardData}>
                  <i className="fa-solid fa-rotate"></i> Refresh
                </button>
                <a 
                  className="btn btn-secondary btn-sm" 
                  href={getCsvDownloadHref()} 
                  download="survey_results.csv"
                >
                  <i className="fa-solid fa-file-export"></i> Export CSV
                </a>
              </div>
            </div>

            <div className="stats-overview-grid">
              <div className="metric-card">
                <div className="metric-icon gradient-1"><i className="fa-solid fa-users"></i></div>
                <div className="metric-info">
                  <h3>{dashboardData ? dashboardData.total_submissions : 0}</h3>
                  <p>Total Evaluators</p>
                </div>
              </div>
              <div className="metric-card">
                <div className="metric-icon gradient-2"><i className="fa-solid fa-volume-high"></i></div>
                <div className="metric-info">
                  <h3>{getTopTtsVoice()}</h3>
                  <p>Top TTS Voice Model</p>
                </div>
              </div>
              <div className="metric-card">
                <div className="metric-icon gradient-3"><i className="fa-solid fa-file-audio"></i></div>
                <div className="metric-info">
                  <h3>{getTopAudioQuality()}</h3>
                  <p>Top Audio Sample Quality</p>
                </div>
              </div>
            </div>

            {/* Dashboard Charts */}
            <div className="dashboard-charts-grid">
              <div className="chart-card">
                <h3>Text-to-Speech (TTS) Mean Opinion Scores</h3>
                <p className="chart-subtitle">Average MOS scores across Naturalness, Pronunciation, Intonation, and Overall Quality (1-5)</p>
                <div className="chart-canvas-container">
                  <canvas ref={ttsChartCanvasRef}></canvas>
                </div>
              </div>
              
              <div className="chart-card">
                <h3>Reference Audio Quality Mean Opinion Scores</h3>
                <p className="chart-subtitle">Average MOS scores across Clarity, Intelligibility, Noise, and Overall Quality (1-5)</p>
                <div className="chart-canvas-container">
                  <canvas ref={sttChartCanvasRef}></canvas>
                </div>
              </div>
            </div>

            {/* Details Statistics Table */}
            <div className="card table-card">
              <div className="card-header table-header">
                <h3><i className="fa-solid fa-table"></i> Detailed Model Statistics</h3>
              </div>
              <div className="card-body no-padding">
                <div className="table-responsive">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Model / File Name</th>
                        <th>Category</th>
                        <th>Overall MOS (1-5)</th>
                        <th>Std Deviation (SD)</th>
                        <th>95% Conf. Interval (CI)</th>
                        <th>Assessments Count</th>
                      </tr>
                    </thead>
                    <tbody>
                      {getDetailsTableRows().length === 0 ? (
                        <tr>
                          <td colSpan="6" className="text-center">No survey results available. Submit a survey to see data.</td>
                        </tr>
                      ) : (
                        getDetailsTableRows().map((row, idx) => (
                          <tr key={idx}>
                            <td><strong>{row.name}</strong></td>
                            <td><span className="badge">{row.category}</span></td>
                            <td>
                              <i className="fa-solid fa-star" style={{ color: "var(--warning)" }}></i>{" "}
                              <strong>{row.mean.toFixed(2)}</strong>
                            </td>
                            <td>&plusmn; {row.std_dev.toFixed(2)}</td>
                            <td>&plusmn; {row.ci_margin.toFixed(2)}</td>
                            <td>{row.count} scores</td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            {/* Comments logs */}
            <div className="card comments-card">
              <div className="card-header">
                <h3><i className="fa-solid fa-comment-dots"></i> Evaluator Feedback & Comments</h3>
              </div>
              <div className="card-body">
                <div className="comments-list-container">
                  {!dashboardData || dashboardData.raw_responses.filter(r => r.comments && r.comments.trim() !== "").length === 0 ? (
                    <div className="text-center text-muted">No comments logged yet.</div>
                  ) : (
                    dashboardData.raw_responses
                      .filter(r => r.comments && r.comments.trim() !== "")
                      .map((c, idx) => (
                        <div className="comment-bubble fade-in" key={idx}>
                          <div className="comment-meta">
                            <span className="user"><i className="fa-solid fa-circle-user"></i> {c.userInfo.name} (Age: {c.userInfo.age})</span>
                            <span className="noise"><i className="fa-solid fa-volume-low"></i> Env: {c.userInfo.noise}</span>
                          </div>
                          <p className="comment-text">"{c.comments}"</p>
                        </div>
                      ))
                  )}
                </div>
              </div>
            </div>

          </section>
        )}

        {currentView === "transcribe" && (
          <section id="transcribe-section" className="app-view active fade-in">
            <div className="card fade-in">
              <div className="card-header gradient-2">
                <h2><i className="fa-solid fa-microphone-lines"></i> Transcribe Custom Audio</h2>
                <p>Upload a custom audio file and run transcription locally with Faster-Whisper.</p>
              </div>
              <div className="card-body">
                <form onSubmit={handleTranscribeSubmit}>
                  <div className="form-group">
                    <label htmlFor="audio-file">Select Audio File (WAV, MP3, M4A, OGG) <span className="required">*</span></label>
                    <input 
                      type="file" 
                      id="audio-file" 
                      accept="audio/*"
                      onChange={(e) => setTranscribeFile(e.target.files[0])}
                      style={{
                        width: "100%",
                        background: "rgba(11, 15, 25, 0.6)",
                        border: "1px dashed var(--border-color)",
                        padding: "20px",
                        borderRadius: "var(--radius-md)",
                        color: "var(--text-secondary)",
                        cursor: "pointer"
                      }}
                    />
                  </div>

                  <div className="form-row">
                    <div className="form-group">
                      <label htmlFor="transcribe-model">Whisper Model</label>
                      <select 
                        id="transcribe-model" 
                        value={transcribeModel}
                        onChange={(e) => setTranscribeModel(e.target.value)}
                      >
                        <option value="tiny">Tiny (Fastest, ~39M params)</option>
                        <option value="base">Base (Balanced, ~74M params)</option>
                        <option value="small">Small (High Accuracy, ~244M params)</option>
                      </select>
                    </div>

                    <div className="form-group">
                      <label htmlFor="transcribe-language">Language (Optional)</label>
                      <select 
                        id="transcribe-language" 
                        value={transcribeLanguage}
                        onChange={(e) => setTranscribeLanguage(e.target.value)}
                      >
                        <option value="">Auto-Detect Language</option>
                        <option value="en">English (en)</option>
                        <option value="es">Spanish (es)</option>
                        <option value="fr">French (fr)</option>
                        <option value="de">German (de)</option>
                        <option value="it">Italian (it)</option>
                        <option value="zh">Chinese (zh)</option>
                        <option value="ja">Japanese (ja)</option>
                        <option value="hi">Hindi (hi)</option>
                      </select>
                    </div>
                  </div>

                  <button 
                    type="submit" 
                    className="btn btn-primary btn-block"
                    disabled={isTranscribing}
                    style={{ marginTop: "10px" }}
                  >
                    {isTranscribing ? (
                      <>
                        <i className="fa-solid fa-circle-notch fa-spin"></i> Transcribing Audio...
                      </>
                    ) : (
                      <>
                        <i className="fa-solid fa-play"></i> Run Transcription
                      </>
                    )}
                  </button>
                </form>
              </div>
            </div>

            {transcribeResult && (
              <div className="card fade-in" style={{ border: "1px solid rgba(16, 185, 129, 0.3)" }}>
                <div className="card-header gradient-1" style={{ borderBottom: "1px solid rgba(16, 185, 129, 0.2)" }}>
                  <h2><i className="fa-solid fa-square-poll-horizontal"></i> Transcription Results</h2>
                  <p>Inference successfully completed on local machine.</p>
                </div>
                <div className="card-body">
                  <div className="stats-overview-grid" style={{ marginBottom: "20px" }}>
                    <div className="metric-card" style={{ padding: "12px 18px", gap: "12px" }}>
                      <div className="metric-icon gradient-1" style={{ width: "35px", height: "35px", fontSize: "14px" }}>
                        <i className="fa-solid fa-language"></i>
                      </div>
                      <div className="metric-info">
                        <h3 style={{ fontSize: "18px" }}>{transcribeResult.language ? transcribeResult.language.toUpperCase() : "N/A"}</h3>
                        <p style={{ margin: 0, fontSize: "10px" }}>Language</p>
                      </div>
                    </div>
                    <div className="metric-card" style={{ padding: "12px 18px", gap: "12px" }}>
                      <div className="metric-icon gradient-2" style={{ width: "35px", height: "35px", fontSize: "14px" }}>
                        <i className="fa-solid fa-clock"></i>
                      </div>
                      <div className="metric-info">
                        <h3 style={{ fontSize: "18px" }}>{transcribeResult.duration ? transcribeResult.duration.toFixed(2) : "0.00"}s</h3>
                        <p style={{ margin: 0, fontSize: "10px" }}>Audio Duration</p>
                      </div>
                    </div>
                    <div className="metric-card" style={{ padding: "12px 18px", gap: "12px" }}>
                      <div className="metric-icon gradient-3" style={{ width: "35px", height: "35px", fontSize: "14px" }}>
                        <i className="fa-solid fa-bolt"></i>
                      </div>
                      <div className="metric-info">
                        <h3 style={{ fontSize: "18px" }}>{transcribeResult.latency ? transcribeResult.latency.toFixed(2) : "0.00"}s</h3>
                        <p style={{ margin: 0, fontSize: "10px" }}>Inference Latency</p>
                      </div>
                    </div>
                  </div>

                  <div className="reference-phrase-box" style={{ background: "rgba(0, 0, 0, 0.2)", padding: "20px" }}>
                    <span className="label" style={{ color: "var(--accent)" }}>Transcribed Text:</span>
                    <blockquote style={{ fontSize: "15px", whiteSpace: "pre-wrap", fontWeight: "normal" }}>
                      {transcribeResult.text || <span className="text-muted" style={{ fontStyle: "italic" }}>No text transcribed.</span>}
                    </blockquote>
                  </div>

                  <button 
                    className="btn btn-secondary btn-block"
                    onClick={() => {
                      navigator.clipboard.writeText(transcribeResult.text || "");
                      alert("Copied to clipboard!");
                    }}
                  >
                    <i className="fa-solid fa-copy"></i> Copy Text to Clipboard
                  </button>
                </div>
              </div>
            )}
          </section>
        )}

        {currentView === "pipeline" && (
          <section id="pipeline-section" className="app-view active fade-in">
            <div className="card fade-in">
              <div className="card-header gradient-3">
                <h2><i className="fa-solid fa-arrows-spin"></i> Unified STT-NLU-TTS Pipeline</h2>
                <p>Upload an audio file to run speech-to-text, extract NLU intent/entities/sentiment, and synthesize a response back to audio.</p>
              </div>
              <div className="card-body">
                <form onSubmit={handlePipelineSubmit}>
                  <div className="form-group">
                    <label htmlFor="pipeline-file">Select Audio File (WAV, MP3, M4A, OGG) <span className="required">*</span></label>
                    <input 
                      type="file" 
                      id="pipeline-file" 
                      accept="audio/*"
                      onChange={(e) => setPipelineFile(e.target.files[0])}
                      style={{
                        width: "100%",
                        background: "rgba(11, 15, 25, 0.6)",
                        border: "1px dashed var(--border-color)",
                        padding: "20px",
                        borderRadius: "var(--radius-md)",
                        color: "var(--text-secondary)",
                        cursor: "pointer"
                      }}
                    />
                  </div>

                  <div className="form-row">
                    <div className="form-group">
                      <label htmlFor="pipeline-voice">TTS Response Voice</label>
                      <select 
                        id="pipeline-voice" 
                        value={pipelineVoice}
                        onChange={(e) => setPipelineVoice(e.target.value)}
                      >
                        <option value="amy">Amy (Medium, female)</option>
                        <option value="danny">Danny (Low, male)</option>
                        <option value="joe">Joe (Medium, male)</option>
                        <option value="lessac">Lessac (Medium, female)</option>
                        <option value="ryan">Ryan (Medium, male)</option>
                      </select>
                    </div>

                    <div className="form-group">
                      <label htmlFor="pipeline-format">TTS Audio Format</label>
                      <select 
                        id="pipeline-format" 
                        value={pipelineFormat}
                        onChange={(e) => setPipelineFormat(e.target.value)}
                      >
                        <option value="wav">WAV (Lossless PCM)</option>
                        <option value="mp3">MP3 (MPEG-3 compressed)</option>
                        <option value="ogg">OGG (Opus compressed)</option>
                      </select>
                    </div>
                  </div>

                  <button 
                    type="submit" 
                    className="btn btn-primary btn-block"
                    disabled={isProcessingPipeline}
                    style={{ marginTop: "10px" }}
                  >
                    {isProcessingPipeline ? (
                      <>
                        <i className="fa-solid fa-circle-notch fa-spin"></i> Processing Pipeline...
                      </>
                    ) : (
                      <>
                        <i className="fa-solid fa-play"></i> Run Pipeline
                      </>
                    )}
                  </button>
                </form>
              </div>
            </div>

            {pipelineResult && (
              <div className="card fade-in" style={{ border: "1px solid rgba(59, 130, 246, 0.3)" }}>
                <div className="card-header gradient-1" style={{ borderBottom: "1px solid rgba(59, 130, 246, 0.2)" }}>
                  <h2><i className="fa-solid fa-circle-check"></i> Processing Results</h2>
                  <p>Unified pipeline completed successfully.</p>
                </div>
                <div className="card-body">
                  <div className="stats-overview-grid" style={{ marginBottom: "20px" }}>
                    <div className="metric-card" style={{ padding: "12px 18px", gap: "12px" }}>
                      <div className="metric-icon gradient-3" style={{ width: "35px", height: "35px", fontSize: "14px" }}>
                        <i className="fa-solid fa-bolt"></i>
                      </div>
                      <div className="metric-info">
                        <h3 style={{ fontSize: "18px" }}>{pipelineResult.latency ? pipelineResult.latency.toFixed(2) : "0.00"}s</h3>
                        <p style={{ margin: 0, fontSize: "10px" }}>Pipeline Latency</p>
                      </div>
                    </div>
                    <div className="metric-card" style={{ padding: "12px 18px", gap: "12px" }}>
                      <div className="metric-icon gradient-2" style={{ width: "35px", height: "35px", fontSize: "14px" }}>
                        <i className="fa-solid fa-music"></i>
                      </div>
                      <div className="metric-info">
                        <h3 style={{ fontSize: "18px" }}>{pipelineResult.audio_format ? pipelineResult.audio_format.toUpperCase() : "WAV"}</h3>
                        <p style={{ margin: 0, fontSize: "10px" }}>Response Audio Format</p>
                      </div>
                    </div>
                  </div>

                  <div className="reference-phrase-box" style={{ background: "rgba(0, 0, 0, 0.2)", padding: "20px", marginBottom: "20px" }}>
                    <span className="label" style={{ color: "var(--accent)" }}>Transcribed Text (STT):</span>
                    <blockquote style={{ fontSize: "16px", whiteSpace: "pre-wrap", fontWeight: "normal", marginTop: "5px" }}>
                      {pipelineResult.input_text || <span className="text-muted" style={{ fontStyle: "italic" }}>No text transcribed.</span>}
                    </blockquote>
                  </div>

                  <div style={{ marginBottom: "25px", background: "rgba(30, 41, 59, 0.4)", padding: "20px", borderRadius: "var(--radius-md)", border: "1px solid var(--border-color)" }}>
                    <h3 style={{ fontSize: "16px", marginBottom: "15px", display: "flex", alignItems: "center", gap: "8px" }}>
                      <i className="fa-solid fa-brain" style={{ color: "var(--accent)" }}></i> NLU Analysis
                    </h3>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px", marginBottom: "15px" }}>
                      <div>
                        <span style={{ fontSize: "12px", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>Intent Classification</span>
                        <div style={{ display: "flex", alignItems: "baseline", gap: "8px" }}>
                          <span style={{ fontSize: "18px", fontWeight: "bold", color: "#fff" }}>
                            {pipelineResult.nlu_data?.intent}
                          </span>
                          <span style={{ fontSize: "12px", color: "rgba(255, 255, 255, 0.5)" }}>
                            (conf: {pipelineResult.nlu_data?.confidence ? (pipelineResult.nlu_data.confidence * 100).toFixed(0) : 0}%)
                          </span>
                        </div>
                      </div>
                      <div>
                        <span style={{ fontSize: "12px", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>Sentiment Analysis</span>
                        <div>
                          <span style={{ 
                            fontSize: "14px", 
                            fontWeight: "bold", 
                            padding: "4px 8px", 
                            borderRadius: "4px",
                            background: pipelineResult.nlu_data?.sentiment?.label === "positive" ? "rgba(16, 185, 129, 0.2)" : pipelineResult.nlu_data?.sentiment?.label === "negative" ? "rgba(239, 68, 68, 0.2)" : "rgba(107, 114, 128, 0.2)",
                            color: pipelineResult.nlu_data?.sentiment?.label === "positive" ? "#10b981" : pipelineResult.nlu_data?.sentiment?.label === "negative" ? "#ef4444" : "#9ca3af",
                            border: `1px solid ${pipelineResult.nlu_data?.sentiment?.label === "positive" ? "rgba(16, 185, 129, 0.3)" : pipelineResult.nlu_data?.sentiment?.label === "negative" ? "rgba(239, 68, 68, 0.3)" : "rgba(107, 114, 128, 0.3)"}`
                          }}>
                            {pipelineResult.nlu_data?.sentiment?.label?.toUpperCase()}
                          </span>
                          <span style={{ fontSize: "12px", color: "rgba(255, 255, 255, 0.5)", marginLeft: "8px" }}>
                            (score: {pipelineResult.nlu_data?.sentiment?.score})
                          </span>
                        </div>
                      </div>
                    </div>

                    <div style={{ marginTop: "15px" }}>
                      <span style={{ fontSize: "12px", color: "var(--text-secondary)", display: "block", marginBottom: "6px" }}>Named Entities</span>
                      {pipelineResult.nlu_data?.entities && pipelineResult.nlu_data.entities.length > 0 ? (
                        <div style={{ overflowX: "auto" }}>
                          <table className="survey-table" style={{ width: "100%", fontSize: "13px" }}>
                            <thead>
                              <tr>
                                <th style={{ padding: "6px 12px" }}>Text</th>
                                <th style={{ padding: "6px 12px" }}>Type</th>
                                <th style={{ padding: "6px 12px" }}>Range</th>
                              </tr>
                            </thead>
                            <tbody>
                              {pipelineResult.nlu_data.entities.map((ent, idx) => (
                                <tr key={idx}>
                                  <td style={{ padding: "6px 12px" }}><strong>{ent.text}</strong></td>
                                  <td style={{ padding: "6px 12px" }}><span className="badge">{ent.label}</span></td>
                                  <td style={{ padding: "6px 12px", color: "rgba(255,255,255,0.4)" }}>[{ent.start}, {ent.end}]</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      ) : (
                        <span style={{ fontSize: "13px", fontStyle: "italic", color: "rgba(255, 255, 255, 0.4)" }}>No named entities extracted.</span>
                      )}
                    </div>

                    <div style={{ marginTop: "15px" }}>
                      <details style={{ cursor: "pointer" }}>
                        <summary style={{ fontSize: "12px", color: "var(--accent)" }}>Show raw NLU JSON structure</summary>
                        <pre style={{ 
                          marginTop: "8px", 
                          background: "rgba(0,0,0,0.4)", 
                          padding: "10px", 
                          borderRadius: "4px", 
                          fontSize: "11px", 
                          overflowX: "auto", 
                          color: "#38bdf8",
                          border: "1px solid rgba(255,255,255,0.05)"
                        }}>
                          {JSON.stringify(pipelineResult.nlu_data, null, 2)}
                        </pre>
                      </details>
                    </div>
                  </div>

                  <div style={{ marginBottom: "15px", background: "rgba(99, 102, 241, 0.15)", padding: "20px", borderRadius: "var(--radius-md)", border: "1px solid rgba(99, 102, 241, 0.3)" }}>
                    <h3 style={{ fontSize: "16px", marginBottom: "10px", display: "flex", alignItems: "center", gap: "8px" }}>
                      <i className="fa-solid fa-volume-high" style={{ color: "var(--accent)" }}></i> Synthesized Response (TTS)
                    </h3>
                    <p style={{ fontSize: "13px", color: "rgba(255, 255, 255, 0.7)", marginBottom: "15px" }}>
                      The text response synthesized by the backend contains transcription details and the NLU intent.
                    </p>
                    {pipelineResult.audio_response_base64 && (
                      <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                        <audio 
                          controls 
                          src={`data:audio/${pipelineResult.audio_format};base64,${pipelineResult.audio_response_base64}`} 
                          style={{ width: "100%", marginTop: "5px" }}
                        />
                        <span style={{ fontSize: "11px", color: "rgba(255,255,255,0.4)", alignSelf: "flex-end" }}>
                          Format: {pipelineResult.audio_format} | Size: {Math.round(pipelineResult.audio_response_base64.length * 0.75 / 1024)} KB
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </section>
        )}

      </main>

      <footer className="app-footer">
        <p>Local Speech Evaluation Pipeline &copy; 2026. Built with React, FastAPI, and Chart.js.</p>
      </footer>
    </>
  );
}
