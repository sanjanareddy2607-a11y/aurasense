"""Report blocks: modules, CSV lab, live monitor, baseline, research centre."""

BLOCKS = [
    {"t": "chapter", "num": "6", "title": "Every module, examined one by one",
     "sub": "What each screen does internally, which files and endpoints implement it, whether the result is real, and where it stops."},

    {"t": "p", "text": "The interface has nine signed-in modules plus public landing, login and registration pages. The table below is the quick map; the sections after it explain each module's internal operation, not just its appearance."},
    {"t": "table", "head": ["Module", "Route", "Primary frontend", "Primary backend", "Nature of result"], "widths": [25, 25, 40, 40, 44], "size": 7.4, "rows": [
        ["Overview", "/app", "pages/Overview.tsx", "analysis, baseline, sessions, model/info", "Real stored records"],
        ["Live Monitor", "/app/monitor", "pages/Monitor.tsx", "sessions router, live.py, simulation.py", "Simulated signals + real inference"],
        ["AI Analysis", "/app/analysis", "pages/Analysis.tsx", "analysis/reference, analysis/demo", "Real model on cached/demo features"],
        ["Analysis detail", "/app/analysis/:id", "pages/AnalysisDetail.tsx", "GET /analysis/{id}, reports", "Real stored result + explanation"],
        ["My Baseline", "/app/baseline", "pages/Baseline.tsx", "baseline service/router", "Real stats over own history"],
        ["BioSignal Lab", "/app/lab", "pages/Lab.tsx", "upload, datasets preview/demo", "Real CSV processing"],
        ["Research Centre", "/app/research", "pages/Research.tsx", "research router, metrics.json", "Real evaluation output"],
        ["Institution Insights", "/app/institution", "pages/Institution.tsx", "aggregate service/router", "Seeded consenting cohort aggregates"],
        ["Reports & History", "/app/reports", "pages/Reports.tsx", "reporting.py, reports router", "Real generated PDFs"],
        ["Settings & Account", "/app/settings", "pages/Settings.tsx", "auth router", "Real account operations"],
    ]},

    {"t": "h2", "text": "6.1 Overview"},
    {"t": "p", "text": "Overview is the home of the signed-in workspace. On load it calls four endpoints in parallel: the eight most recent analyses, the baseline payload, six recent sessions and model information. It shows the latest estimate, signal quality, probability history, stored-analysis count, a trend chart, a model card and a recent-record table."},
    {"t": "b", "items": [
        "Who it is for: every signed-in user.",
        "What the buttons do: rows link to analysis detail or sessions; \u201cStart monitoring\u201d goes to Live Monitor; \u201cOpen lab\u201d goes to BioSignal Lab.",
        "Backend: GET /api/analysis?limit=8, GET /api/baseline, GET /api/sessions?limit=6, GET /api/model/info.",
        "Data: the user's own analysis and session rows plus their baseline. Demo records are labelled as seeded.",
        "ML: none directly; it displays stored model outputs and the model version.",
        "Status: fully functional. If the model artifact is missing, model information reports unavailable and analysis screens explain the setup step.",
    ]},

    {"t": "h2", "text": "6.2 Live Monitor"},
    {"t": "p", "text": "Live Monitor starts a server-side simulated session, requests a new five-second chunk every 3.4 seconds, and draws ECG, EDA, respiration and motion waveforms. After 30 seconds it begins showing model estimates, and prediction history accumulates. Finish/pause/resume/stop are real session state transitions; finishing writes an analysis."},
    {"t": "b", "items": [
        "Who it is for: demonstration and teaching; any signed-in user.",
        "Scenarios: resting, increased arousal, movement/activity, poor contact/noisy, recovery after arousal.",
        "Capture: POST /api/sessions with the scenario; POST /api/sessions/{id}/tick with tick_seconds=5; POST pause/resume/stop.",
        "Signal source: services/simulation.py, deterministic seeds, 250 Hz ECG and 4 Hz other channels. No hardware.",
        "ML: every tick after 30 seconds extracts features and calls the real model; finish uses the full window.",
        "Limitation: synthetic signals are illustrative. The activity and noisy scenarios are not guaranteed to classify as their labels, and the saved session CSV retains only EDA, respiration, temperature and accelerometer magnitude, not ECG.",
    ]},

    {"t": "h2", "text": "6.3 AI Analysis and analysis detail"},
    {"t": "p", "text": "The Analysis workspace has two tabs. \u201cWESAD reference\u201d lets the user choose a participant and optional condition, then calls POST /api/analysis/reference. \u201cDatasets\u201d lists the reference dataset and demonstration recordings; running one calls POST /api/analysis/demo. Both navigate to a detail page that fetches the stored record."},
    {"t": "b", "items": [
        "The reference path samples one matching cached WESAD feature row; it does not re-read raw WESAD signals.",
        "The demo path re-reads a stored demo CSV and runs the same pipeline as an upload.",
        "Detail page shows class, confidence, entropy uncertainty, class probabilities, quality issues, measured features, imputed features, local occlusion contributions, global importance, provenance and model version.",
        "The PDF button calls POST /api/reports/analysis/{id}; history is the recent list on the workspace and the Reports page.",
        "Limitation: a single cached window is a random sample, so repeated reference runs can produce different predictions; there is no seed control in the UI.",
    ]},

    {"t": "h2", "text": "6.4 My Baseline"},
    {"t": "p", "text": "My Baseline summarises the user's own recent analyses as feature means and standard deviations, shows a reliability tier, lists notable deviations in the latest analysis, and plots a trend. Recalibrate writes a versioned BaselineRecord; Reset deactivates the active record without deleting it."},
    {"t": "b", "items": [
        "Data: up to 12 most recent analyses with quality \u2265 40 and a predicted class; features need at least 3 values to appear.",
        "Thresholds: minimum 3 analyses to compute; the profile default is 5; 5\u20139 common sessions = provisional, 10+ = moderate.",
        "Comparison: z-score = (current value \u2212 baseline mean) / baseline SD; |z| \u2265 1 is called notable.",
        "Stored: yes, as a versioned baseline row. Automatic update: no; GET may compute a live display aggregate, but a stored version is created only by recalibrate.",
        "Limitation: it is exploratory and not a clinical norm; it does not separate resting from stress recordings, so mixing contexts weakens interpretation.",
    ]},

    {"t": "h2", "text": "6.5 BioSignal Lab"},
    {"t": "p", "text": "BioSignal Lab is the real upload path. A user drops a .csv/.tsv/.txt file, optionally enters a title and sampling rate, and presses Analyse signal. The file is validated, stored, parsed, mapped to channels, windowed, scored, analysed and saved. The response includes an inspection panel and channel preview."},
    {"t": "b", "items": [
        "Files: POST /api/analysis/upload (multipart); dataset listing GET /api/datasets; preview GET /api/datasets/{id}/preview.",
        "UI: drag-and-drop or file picker, title field, optional Hz field, quality issues, row/duration/rate/window stats, per-channel waveform preview and feature table.",
        "ML: real model inference on the extracted upload features, not on simulated data.",
        "Storage: the raw upload is written to backend/storage/uploads with a UUID prefix and remains there.",
        "Limitation: units are assumed, not converted; unsupported channels are ignored; long files are capped at 12 MB and 400,000 rows.",
    ]},

    {"t": "h2", "text": "6.6 Research Centre"},
    {"t": "p", "text": "The Research Centre presents the evidence behind the model: dataset summary, model comparison, confusion matrix, per-class and per-participant results, permutation importance, experiment history and a research PDF. A researcher can rerun a selected model on the cached feature table with grouped folds; the API stores the resulting experiment."},
    {"t": "b", "items": [
        "Read endpoints: GET /api/research/overview, /metrics, /experiments, /experiments/{id}.",
        "Write endpoint: POST /api/research/experiments, restricted to researcher/admin.",
        "Metric source: ml/artifacts/metrics.json for the trained comparison; experiment rows for reruns.",
        "The 3 seeded experiments are copies of the real training results; new experiments genuinely retrain and use 3-fold GroupKFold.",
        "Limitation: anyone signed in can view metrics; only researchers can run experiments. No experiment queue or background job exists.",
    ]},

    {"t": "h2", "text": "6.7 Institution Insights"},
    {"t": "p", "text": "Institution Insights is role-gated to researcher/admin. It reads weekly aggregates for users whose profile has share_aggregate=true, suppresses weeks with fewer than 5 sessions or fewer than 3 distinct participants, and offers CSV and PDF export. An individual account sees an explanatory restriction page and the API returns 403."},
    {"t": "b", "items": [
        "Endpoints: GET /api/institution/overview?weeks=8, GET /api/institution/export, POST /api/reports/institution.",
        "Displayed: sessions, participants, consenting users, mean stress-associated probability, mean quality, class composition, sources, suppressed-group count and privacy note.",
        "Data: seeded demonstration cohort (12 users) plus opted-in demo accounts; demo sessions are flagged.",
        "Limitation: the summary totals include every opted-in analysis in the window, including those from weeks suppressed in the weekly table. This is a privacy-reporting gap discussed in Chapter 11.",
    ]},

    {"t": "h2", "text": "6.8 Reports & History"},
    {"t": "p", "text": "Reports & History lists the user's report records, links each to its source analysis, regenerates analysis PDFs, downloads files and deletes reports. Researchers/admins can also generate research and institution reports from their modules."},
    {"t": "b", "items": [
        "Endpoints: GET /api/reports, POST /api/reports/analysis/{id}, /research, /institution, GET /api/reports/{id}/download, DELETE /api/reports/{id}.",
        "PDF engine: fpdf2 builds vector pages with header/footer, probabilities, quality, local contributions, global importance and limitations.",
        "Ownership: every report query checks report.user_id; another user's report returns 404.",
        "Status: real generation and download. Files inspected: 1.9\u20136.0 KB, 1\u20133 pages.",
        "Limitation: PDF files are not encrypted; deleting an account removes report rows but not all files on disk.",
    ]},

    {"t": "h2", "text": "6.9 Settings, authentication and account management"},
    {"t": "p", "text": "Settings edits the display name, organisation, aggregate sharing, raw-signal retention, baseline permission, minimum baseline sessions and a private data note. It can change the password, export all personal data as JSON, and delete the account after password confirmation. Registration and login are real, with JWT bearer tokens."},
    {"t": "b", "items": [
        "Endpoints: PATCH /api/auth/profile, POST /api/auth/password, GET /api/auth/export, DELETE /api/auth/account.",
        "Security: PBKDF2-HMAC-SHA256, 260,000 iterations, per-user salt; HS256 JWT valid for 720 minutes; passwords need 8+ characters with a letter and a number.",
        "Restriction: demo accounts cannot be deleted. Admin accounts cannot be self-registered; the institution account is seeded.",
        "Limitation: no email verification, no password reset, no login rate limit, no token revocation, and the token is kept in localStorage.",
    ]},

    {"t": "h2", "text": "How the modules depend on one another"},
    {"t": "p", "text": "Every path that produces a result (live stop, reference analysis, demo analysis, upload) writes the same AnalysisResult table. Overview, Baseline, Reports, Institution and the analysis detail page all read from that shared record. This is why the modules feel connected: they are views over one analysis model rather than separate demos. The model artifact is the other shared dependency; if model.joblib is missing, analysis and live predictions stop while history and reports still open."},

    {"t": "chapter", "num": "7", "title": "BioSignal Lab: the complete CSV upload audit",
     "sub": "Exactly what file can be uploaded, how it is validated and processed, where it is stored, and what errors are possible."},

    {"t": "h2", "text": "What the implementation actually accepts"},
    {"t": "table", "head": ["Rule", "Actual behaviour", "Source"], "widths": [40, 104, 30], "rows": [
        ["File extension", ".csv, .tsv or .txt; anything else returns 415", "routers/analysis.py"],
        ["Size limit", "12 MB (MAX_UPLOAD_BYTES, configurable)", "config.py"],
        ["Row limit", "At least 20 rows, at most 400,000 rows; empty file returns 422", "routers/analysis.py"],
        ["Header row", "Required; the first row is interpreted as column names", "pandas read_csv"],
        ["Delimiter", "Automatically detected with sep=None and the Python engine; a plain comma parse is attempted as fallback", "_read_frame"],
        ["Timestamp", "Optional, but strongly recommended; recognised names include time, timestamp, t, time_s, times, seconds, elapsed", "features.TIME_ALIASES"],
        ["Sampling rate", "Derived from the time column if possible; otherwise the optional upload field; otherwise 64 Hz with a visible \u201cdefault assumption\u201d", "features.infer_fs"],
        ["Recognised channels", "ECG/EKG, BVP/PPG, EDA/GSR/SC/SCL, Resp/RSP, Temp, EMG, HR/Pulse, ACC_x/y/z", "features.ALIASES"],
        ["At least one channel", "Required; otherwise 422 with the expected names", "routers/analysis.py"],
        ["Units", "Not validated or converted; conventional units are assumed", "ml/features.py"],
        ["Multichannel alignment", "Assumed to share a row timeline; there is no per-channel resampling except the single inferred rate", "features_from_frame"],
        ["Missing values", "Interpolated within a channel; heavy gaps reduce quality", "clean_array / assess_quality"],
        ["Window size", "60 s with 30 s stride; short recordings form one shorter window", "features_from_frame"],
        ["Minimum useful duration", "20 s is treated as the minimum for a stable estimate; under that is a critical quality issue", "assess_quality"],
        ["Stored file", "Yes, permanently under storage/uploads with a UUID filename", "routers/analysis.py"],
        ["Auto-deleted?", "No. There is no retention job.", "audit finding"],
        ["Reaches the model?", "Yes. Every valid upload is windowed, featurised and passed to the real model.", "analyse_dataframe"],
    ]},

    {"t": "h2", "text": "Column names: fixed or configurable?"},
    {"t": "p", "text": "Column names are not user-configurable in the UI. The parser normalises a header by lowercasing it and removing non-alphanumeric characters, then looks for known aliases. For example, \u201cHeart Rate (bpm)\u201d becomes heartratebpm and maps to hr; \u201cGSR\u201d maps to eda; \u201cACC_x\u201d maps to accelerometer x. If an accelerometer is provided, all three axes ACC_x, ACC_y and ACC_z are required; otherwise motion features are absent. Extra columns are ignored but listed as unrecognised in the inspection response."},
    {"t": "table", "head": ["Channel", "Accepted aliases (examples)", "Purpose in the model"], "widths": [38, 78, 58], "rows": [
        ["ECG", "ECG, EKG, ECGSignal, ChestECG", "Heart rate and HRV through R-peak detection"],
        ["BVP / PPG", "BVP, PPG, bloodvolumepulse, pulsewave", "Cardiac features when ECG is absent"],
        ["EDA", "EDA, GSR, SCL, electrodermal, skinconductance", "Skin-conductance level, slope, phasic activity, SCRs"],
        ["Respiration", "Resp, respiration, RSP, breathing", "Breathing rate, variability and amplitude"],
        ["Temperature", "Temp, temperature, skintemp, bodytemp", "Mean, variability and trend"],
        ["EMG", "EMG, muscleactivity", "Muscle activity RMS"],
        ["Heart rate", "HR, heartrate, pulse, hrbpm", "Mean and SD of an already-derived HR series"],
        ["Accelerometer", "ACC_x/y/z, accelx, accelerationx, xaxis", "Movement magnitude and variability"],
    ]},

    {"t": "h2", "text": "A template that matches this implementation"},
    {"t": "p", "text": "The following header and rows are valid for AuraSense because time_s is recognised, ECG/EDA/Resp/Temp are recognised, and ACC_x/y/z form a complete accelerometer. Values are illustrative, not a real recording. At 250 Hz, one second needs 250 rows, so this five-row snippet is only a format illustration."},
    {"t": "table", "head": ["time_s", "ECG", "EDA", "Resp", "Temp", "ACC_x", "ACC_y", "ACC_z"], "widths": [20, 24, 20, 20, 20, 22, 22, 22], "size": 7.2, "rows": [
        ["0.000", "0.031", "2.41", "0.12", "33.40", "0.010", "0.008", "0.998"],
        ["0.004", "0.044", "2.41", "0.13", "33.40", "0.011", "0.007", "0.997"],
        ["0.008", "1.020", "2.42", "0.14", "33.40", "0.010", "0.009", "0.999"],
        ["0.012", "-0.180", "2.42", "0.15", "33.40", "0.012", "0.008", "0.998"],
        ["0.016", "0.050", "2.42", "0.16", "33.40", "0.011", "0.008", "0.997"],
    ]},
    {"t": "callout", "title": "How to prepare this in Excel or Google Sheets", "tone": "forest", "text": "Put each column name in the first row exactly as shown (time_s, ECG, EDA, Resp, Temp, ACC_x, ACC_y, ACC_z). Paste one row per sample in time order. Keep timestamps increasing and evenly spaced; do not add units or text inside numeric cells. Save as CSV UTF-8 (Excel: File \u2192 Save As \u2192 CSV UTF-8). Upload the file and leave the sampling-rate field blank so AuraSense reads it from time_s. For a 60-second window at 250 Hz you need 15,000 rows; 90 seconds gives two overlapping windows."},

    {"t": "h2", "text": "What happens step by step after pressing Analyse"},
    {"t": "flow", "title": "Upload processing path", "per_row": 4, "steps": [
        "Choose file\n.csv/.tsv/.txt",
        "Validate size,\nextension, rows",
        "Parse header\nand delimiter",
        "Map aliases to\nphysiological channels",
        "Infer sampling rate\ntime \u2192 hint \u2192 64 Hz",
        "Save raw file\nto storage/uploads",
        "Create Dataset row\n+ metadata",
        "Build 60 s windows\n30 s stride",
        "Extract 20 features\nper window",
        "Score quality\nand gaps",
        "Impute medians\npredict_proba",
        "Aggregate weighted\nprobabilities",
        "Persist Analysis\nwith provenance",
        "Return inspection\n+ preview + result",
    ]},

    {"t": "h2", "text": "Errors a user can encounter"},
    {"t": "table", "head": ["Situation", "HTTP status", "Message / behaviour"], "widths": [66, 22, 86], "rows": [
        ["Unsupported extension", "415", "\u201cOnly .csv, .tsv and .txt files are supported.\u201d"],
        ["Empty file", "422", "\u201cThe uploaded file is empty.\u201d"],
        ["File above 12 MB", "413", "Reports the configured megabyte limit."],
        ["Fewer than 20 rows", "422", "\u201cAt least 20 rows are required to analyse a signal.\u201d"],
        ["More than 400,000 rows", "413", "Asks the user to trim or resample."],
        ["Unparseable content", "422", "Explains the required header row and comma/tab format."],
        ["No recognised channel", "422", "Lists expected ECG/BVP/EDA/Resp/Temp/EMG/ACC/HR names."],
        ["File too short to window", "422", "Raised by the pipeline if no window can be formed."],
        ["All values invalid / channel unusable", "Analysis still runs or 422", "Quality penalty and imputation; if both cardiac and EDA are imputed, the result is Insufficient signal quality."],
        ["Another user's dataset", "403 / 404", "Dataset access is owner-checked; analysis detail returns 404."],
    ]},

    {"t": "h2", "text": "Where the file goes, and what is missing"},
    {"t": "p", "text": "The raw upload is stored at backend/storage/uploads/{uuid}_{safe_filename}. Its Dataset row records the original filename, size, row count, columns, detected channels, assumed sampling rate and uploader. The analysis row stores the extracted features, probabilities, quality and explanation. The UI says \u201cSignals are stored locally on this server\u201d, which is accurate."},
    {"t": "b", "items": [
        "Files are not automatically deleted after processing.",
        "The store_raw_signals privacy toggle controls whether a simulated session retains a CSV; it does not prevent uploaded files from being stored.",
        "Deleting an analysis or account does not remove the uploaded file from disk.",
        "There is no upload virus scan, content-type enforcement beyond extension, or per-user storage quota.",
        "There is no CSV template download button in the interface; the template above is derived from the parser and can be used for a demonstration.",
    ]},

    {"t": "chapter", "num": "8", "title": "Live Monitor: what is really happening",
     "sub": "Simulated physiology, real preprocessing, real inference \u2014 and no hardware at all."},

    {"t": "h2", "text": "Does it use wearable sensors or hardware?"},
    {"t": "p", "text": "No. There is no Bluetooth, Web Bluetooth, USB serial, camera, microphone or phone-sensor code. The browser only receives JSON from the API. The server generates the signals mathematically. Every session row has data_source \u201csimulated\u201d and is_simulation true, and every tick response repeats is_simulation true."},

    {"t": "h2", "text": "How the signals are generated"},
    {"t": "b", "items": [
        "ECG is synthesised at 250 Hz as a sequence of Gaussian P, Q, R, S and T waves at a scenario-specific heart rate, with respiratory sinus modulation, baseline wander and Gaussian noise. Dropout can replace samples with NaN.",
        "EDA is generated at 4 Hz with a slow baseline, noise and scenario-specific skin-conductance responses modelled as a difference of exponentials.",
        "Respiration is a 4 Hz sine wave with a harmonic and noise. Temperature is a 4 Hz slow drift around 33.4 \u00b0C. Accelerometer is a 4 Hz three-axis signal with motion-dependent noise.",
        "Randomness is seeded from the session ID, scenario time and a fixed salt, so a given session produces repeatable chunks rather than independent random noise.",
        "The display downsamples the last eight seconds of ECG to roughly 220 points; the server still analyses the full-resolution generated window.",
    ]},

    {"t": "h2", "text": "What happens when monitoring starts and stops"},
    {"t": "flow", "title": "Live session lifecycle", "per_row": 4, "steps": [
        "Press Start\nselect scenario",
        "POST /sessions\nstatus=active",
        "Every 3.4 s\nPOST tick (5 s)",
        "Server generates\nnew time window",
        "Extract features\n+ quality",
        "After 30 s\nrun real model",
        "Update waveforms,\nHR, history, quality",
        "Press Finish\nPOST /stop",
        "Analyse full window\nstore AnalysisResult",
        "Status=completed\nlink to detail",
    ]},
    {"t": "p", "text": "Ticks advance the stored duration by five seconds but the client sends them every 3.4 seconds, so the displayed elapsed time moves faster than wall-clock time. This is a demonstration choice, not a timestamp bug. Pause stops further ticks; resume restarts them. Starting a new session aborts any previous active/paused session for that user."},

    {"t": "h2", "text": "Scenarios and their intended quality/class"},
    {"t": "table", "head": ["Scenario", "Intended physiology", "Expected outcome (not guaranteed)"], "widths": [38, 100, 36], "rows": [
        ["resting", "HR 62, low EDA, steady breathing", "neutral-associated"],
        ["arousal", "HR 92, reduced HRV, rising EDA, faster breathing", "stress-associated"],
        ["activity", "HR 112 with high movement/noise", "ambiguous; may look neutral or stressed"],
        ["noisy", "Disconnected EDA, motion-corrupted ECG, 28% dropout", "insufficient quality"],
        ["recovery", "HR 88 declining toward rest, moderate EDA", "transitional"],
    ]},
    {"t": "p", "text": "The scenarios are illustrations, not a validated stress induction protocol. The application itself warns that activity and noise can mimic arousal. During the earlier manual verification a resting session completed with a neutral-associated estimate and 100/100 quality; this audit did not create a new session, to avoid changing the demonstration database."},

    {"t": "h2", "text": "What is real and what is not"},
    {"t": "table", "head": ["Element", "Real or simulated?"], "widths": [70, 104], "rows": [
        ["ECG/EDA/resp/temp/ACC samples", "Simulated mathematical signals"],
        ["Waveforms and heart-rate dots", "Derived from simulated samples"],
        ["Quality score", "Real computation on simulated samples"],
        ["Features and class prediction", "Real code and real trained model on simulated samples"],
        ["Stored analysis and report", "Real database row and real PDF"],
        ["Connection to a person or wearable", "None"],
        ["Saved session CSV contents", "EDA, Resp, Temp and ACC magnitude only; ECG is not saved"],
    ]},

    {"t": "chapter", "num": "9", "title": "My Baseline and personalisation",
     "sub": "What a personal baseline is, how this implementation computes it, and how far the personalisation actually goes."},

    {"t": "h2", "text": "What a physiological baseline means"},
    {"t": "p", "text": "A baseline is a person's usual range for measurements such as resting heart rate, HRV and skin conductance. Two healthy people can differ substantially: one may rest at 58 bpm and another at 78 bpm. Comparing a reading with the person's own history can be more informative than comparing both people with one population average. It does not tell us why a reading changed."},

    {"t": "h2", "text": "How AuraSense calculates it"},
    {"t": "b", "items": [
        "It takes the user's 12 most recent analyses that have quality \u2265 40 and a non-null predicted class.",
        "For each of the 20 features it collects all finite values across those analyses. A feature appears only if it has at least 3 values.",
        "It stores the mean, sample standard deviation, minimum, maximum and count, with the human label, unit and group.",
        "A BaselineRecord stores this JSON summary, the analysis IDs used, a version number and an active flag. Older records are deactivated when a new version is created.",
        "The API requires at least 3 usable analyses to recalibrate; the profile default minimum is 5. Reliability is \u201cinsufficient\u201d below the minimum, \u201cprovisional\u201d within 5 sessions of it, and \u201cmoderate\u201d at 10 or more.",
    ]},

    {"t": "h2", "text": "How new readings are compared"},
    {"t": "p", "text": "The latest analysis is compared feature by feature with the baseline mean and standard deviation. The z-score is (current \u2212 mean) / SD. Values with |z| \u2265 1 are listed as notable, up to six; the comparison table shows the top ten by absolute z-score. This is a descriptive deviation, not a diagnostic threshold. For example, if Meera's baseline HR mean is 62 bpm with SD 4 and a reading is 74 bpm, z = 3.0, so the app flags a large positive deviation. If another person's baseline is 80 \u00b1 10 and their reading is also 74, z = \u22120.6, which is unremarkable for them."},

    {"t": "h2", "text": "Is it genuinely personalised?"},
    {"t": "p", "text": "Partly. The statistics are computed from that user's own stored analyses, so the reference range is personal. However, the model's class prediction is not personalised: it always uses the same WESAD-trained model. The baseline only changes the comparison display and the trend, not the classifier's decision. The app does not use the baseline to adapt or retrain the model, and it does not require recordings to be resting-state, so a mixture of stress and calm sessions can widen the range."},

    {"t": "h2", "text": "Storage, updates and configurable thresholds"},
    {"t": "table", "head": ["Question", "Answer"], "widths": [66, 108], "rows": [
        ["Stored?", "Yes, in the baselines table with JSON features and a version."],
        ["Updated automatically?", "No. GET /baseline can display a live aggregate if no active record exists, but only POST /recalibrate writes a record."],
        ["How many readings?", "Minimum 3; profile default 5; up to 12 most recent are used."],
        ["Which features?", "All 20, when each has at least 3 finite values."],
        ["Which analyses?", "Any own analysis with quality \u2265 40 and a predicted class, including simulated, uploaded and reference analyses."],
        ["Thresholds configurable?", "Minimum sessions (3\u201320) and allow/deny baseline are configurable in Settings. The quality threshold and z \u2265 1 are fixed in code."],
        ["Same thresholds everywhere?", "Quality 40 is also the reliability gate for classification, but z-scores are used only for baseline comparison. No global stress threshold is applied."],
        ["Can it be disabled or reset?", "Yes. allow_baseline disables it; Reset deactivates active records without deleting analyses."],
    ]},
    {"t": "callout", "title": "Honest description for faculty", "tone": "amber", "text": "The baseline is a personal reference-range display, not an adaptive learning system. It helps a user see whether a new reading differs from their own history, but it does not make the underlying stress-pattern model more accurate for that person, and it has not been validated as a personalised stress detector."},

    {"t": "chapter", "num": "10", "title": "Research Centre and scientific evaluation",
     "sub": "How the metrics are calculated, why participant-independent folds matter, and exactly where each displayed number comes from."},

    {"t": "h2", "text": "Which models are compared and how"},
    {"t": "table", "head": ["Model", "Configuration", "Role"], "widths": [40, 104, 30], "rows": [
        ["Random Forest", "300 trees, min_samples_leaf=2, sqrt features, balanced subsample", "Non-linear ensemble baseline"],
        ["Support Vector Machine", "RBF kernel, C=2.0, probability=True, median imputer + standard scaler", "Margin-based comparison"],
        ["Gradient Boosting", "HistGradientBoosting, 300 iterations, lr 0.08, 31 leaves, L2 1.0", "Selected model"],
        ["XGBoost", "Conditional code only; xgboost not installed", "Unavailable; skipped"],
    ]},
    {"t": "p", "text": "Each model is trained five times. In each fold, 12 participants train the model and 3 are held out; their windows are predicted out-of-fold. The pooled out-of-fold predictions produce the accuracy, balanced accuracy, macro precision/recall/F1, per-class metrics and the 3\u00d73 confusion matrix. Fold-level accuracy and balanced accuracy are also recorded."},

    {"t": "h2", "text": "Are accuracy and balanced accuracy real?"},
    {"t": "p", "text": "Yes. Both are computed with scikit-learn from the pooled predictions, not typed into the UI. Accuracy is the fraction of all windows whose predicted class matches the WESAD label. Balanced accuracy is the unweighted mean of per-class recall, so the small amusement class counts as much as neutral. This is why Random Forest has 82.4% accuracy but only 69.7% balanced accuracy: it detects neutral and stress well but rarely amusement."},

    {"t": "h2", "text": "Where each displayed number comes from"},
    {"t": "table", "head": ["Displayed item", "Source", "Calculated?"], "widths": [50, 88, 36], "rows": [
        ["Accuracy / balanced accuracy / F1", "metrics.json \u2192 ml/train.py _metrics()", "Yes, scikit-learn"],
        ["Per-class precision/recall/F1", "Confusion matrix cells in _metrics()", "Yes"],
        ["Confusion matrix", "confusion_matrix(y_true, y_pred, labels)", "Yes"],
        ["Per-participant scores", "Masked out-of-fold predictions per subject", "Yes"],
        ["Feature importance", "permutation_importance, 8 repeats, held-out folds", "Yes"],
        ["Class distribution", "pandas value_counts on labels", "Yes"],
        ["Model version", "Generated from date + deterministic hash suffix", "Yes"],
        ["Dataset summary", "dataset_summary.json generated by extraction", "Yes"],
        ["Experiment results", "ResearchExperiment row created by GroupKFold rerun", "Yes"],
        ["Citation URLs", "Static references", "No \u2014 citations, not metrics"],
    ]},

    {"t": "h2", "text": "Confusion matrix and class weaknesses"},
    {"t": "p", "text": "For Gradient Boosting, rows are actual neutral/stress/amusement and columns are predicted neutral/stress/amusement: [[488,29,45],[7,280,20],[51,26,86]]. Stress recall is high (280 of 307 stress windows), while amusement recall is only 86 of 163. Forty-five neutral windows were called amusement and 51 amusement windows were called neutral, showing the overlap between calm and positive affect in these features. This is honest, useful evidence, not a failure hidden by the UI."},

    {"t": "h2", "text": "Is SHAP implemented?"},
    {"t": "p", "text": "No. SHAP is not installed. Local explanations use occlusion: each feature is set to its training median and the change in the predicted-class probability is recorded. Global importance uses permutation importance. Both are real, model-agnostic techniques, and both are labelled accurately in the interface and PDFs. They answer \u201cwhat does the model rely on?\u201d, not \u201cwhat caused this physiology?\u201d"},

    {"t": "h2", "text": "Validation, leakage and reproducibility"},
    {"t": "table", "head": ["Question", "Finding"], "widths": [54, 120], "rows": [
        ["Validation technique", "5-fold GroupKFold by participant for training; 3-fold GroupKFold for UI-rerun experiments."],
        ["Participant-independent?", "Yes. No participant appears in both training and test within a fold."],
        ["Window leakage?", "Adjacent 60 s windows overlap by 30 s and are correlated; GroupKFold removes participant leakage but not within-condition similarity."],
        ["Model-selection leakage?", "The best model is chosen using the same grouped CV that produces the reported score; there is no nested selection loop, so the selection itself is slightly optimistic."],
        ["Hyperparameter tuning?", "No search; fixed sensible defaults. This reduces tuning leakage but is not optimised."],
        ["Reproducible?", "Yes for the fixed feature CSV, random_state=42 and the same scikit-learn version. Reference analysis window sampling is random and not seeded in the API."],
        ["Dataset version recorded?", "Yes: model artifact and metrics include windows, participants, classes and timestamps."],
        ["External validation?", "None. There is no second dataset, device or population."],
    ]},
    {"t": "callout", "title": "What a researcher should say", "tone": "coral", "text": "These are participant-independent laboratory results on 15 people and 1,032 overlapping windows. They are reproducible and honestly computed, but they are not evidence of everyday or clinical accuracy. Balanced accuracy around 77% is a credible prototype result, not a product claim."},

    {"t": "p", "text": "To reproduce, run `python -m ml.wesad_extract` (reads the local WESAD folder and writes cached CSVs), then `python -m ml.train` (writes model.joblib and metrics.json). The training script prints fold progress and model scores. The frontend does not retrain anything; it reads the saved result."},
]
