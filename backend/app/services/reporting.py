"""PDF report generation with fpdf2."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from fpdf import FPDF
from sqlalchemy.orm import Session

from ..config import settings
from ..models import AnalysisResult, Dataset, Report, ResearchExperiment, User
from ml.features import FEATURE_META

FOREST = (24, 61, 50)
SAGE = (145, 165, 142)
CHARCOAL = (48, 56, 50)
GREY = (133, 139, 131)
AMBER = (212, 154, 69)
CORAL = (201, 121, 105)
LINE = (224, 222, 213)


def _s(value) -> str:
    text = str(value if value is not None else "")
    for source, target in {"\u2013": "-", "\u2014": "-", "\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"', "\u2265": ">=", "\u2264": "<=", "\u00b1": "+/-", "\u2192": "->"}.items():
        text = text.replace(source, target)
    return text.encode("latin-1", "replace").decode("latin-1")


class ReportPDF(FPDF):
    def header(self) -> None:
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*GREY)
        self.cell(0, 6, _s("AuraSense  |  Beyond the pulse. Understand the pattern."), align="L")
        self.ln(5)
        self.set_draw_color(*LINE)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def footer(self) -> None:
        self.set_y(-16)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*GREY)
        self.cell(
            0,
            8,
            _s(
                f"AuraSense research report  |  page {self.page_no()}  |  Not a medical device  |  Not a diagnosis"
            ),
            align="C",
        )


def _new_pdf() -> ReportPDF:
    pdf = ReportPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(14, 16, 14)
    pdf.add_page()
    return pdf


def _title(pdf: ReportPDF, title: str, subtitle: str | None = None) -> None:
    pdf.set_font("Helvetica", "B", 21)
    pdf.set_text_color(*FOREST)
    pdf.multi_cell(0, 9, _s(title), new_x="LMARGIN", new_y="NEXT")
    if subtitle:
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*GREY)
        pdf.multi_cell(0, 5, _s(subtitle), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)


def _h2(pdf: ReportPDF, text: str) -> None:
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*FOREST)
    pdf.cell(0, 7, _s(text), new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*LINE)
    pdf.line(14, pdf.get_y(), 196, pdf.get_y())
    pdf.ln(3)


def _para(pdf: ReportPDF, text: str, size: int = 9.5, color=CHARCOAL) -> None:
    pdf.set_font("Helvetica", "", size)
    pdf.set_text_color(*color)
    pdf.multi_cell(0, 5, _s(text), new_x="LMARGIN", new_y="NEXT")


def _kv(pdf: ReportPDF, rows: list[tuple[str, str]]) -> None:
    pdf.set_font("Helvetica", "", 9)
    for label, value in rows:
        pdf.set_text_color(*GREY)
        pdf.cell(52, 6, _s(label), border=0)
        pdf.set_text_color(*CHARCOAL)
        pdf.multi_cell(0, 6, _s(value), border=0, new_x="LMARGIN", new_y="NEXT")


def _badge(pdf: ReportPDF, text: str, color=FOREST) -> None:
    pdf.set_fill_color(*color)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 9)
    width = max(28, pdf.get_string_width(_s(text)) + 12)
    pdf.cell(width, 8, _s(text), fill=True, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)


def _bar(pdf: ReportPDF, label: str, share: float, value_text: str, color=FOREST) -> None:
    share = max(0.0, min(1.0, share))
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*CHARCOAL)
    pdf.cell(72, 5.5, _s(label[:52]))
    pdf.cell(20, 5.5, _s(value_text), align="R")
    x = pdf.get_x() + 3
    y = pdf.get_y() + 1.6
    width = 88
    pdf.set_fill_color(236, 234, 226)
    pdf.rect(x, y, width, 3.4, style="F")
    pdf.set_fill_color(*color)
    pdf.rect(x, y, max(0.4, width * share), 3.4, style="F")
    pdf.ln(6)


def _confusion(pdf: ReportPDF, matrix: list[list[int]], classes: list[str]) -> None:
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_text_color(*CHARCOAL)
    pdf.cell(36, 6, "actual \\ predicted")
    for name in classes:
        pdf.cell(28, 6, _s(name), align="C")
    pdf.ln(6)
    pdf.set_font("Helvetica", "", 8.5)
    for idx, name in enumerate(classes):
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.cell(36, 6, _s(name))
        pdf.set_font("Helvetica", "", 8.5)
        for j in range(len(classes)):
            value = matrix[idx][j] if idx < len(matrix) and j < len(matrix[idx]) else 0
            pdf.cell(28, 6, str(value), align="C")
        pdf.ln(6)
    pdf.ln(2)


def _save(pdf: ReportPDF, report: Report) -> str:
    settings.ensure_dirs()
    path = settings.storage_dir / "reports" / f"{report.id}.pdf"
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(path))
    return str(path)


DISCLAIMER = (
    "AuraSense estimates similarity between a signal window and patterns learned from the WESAD laboratory "
    "dataset. It does not measure a mental state, diagnose any condition, or replace professional advice. "
    "Heart rate, HRV and electrodermal activity are also affected by movement, caffeine, illness, temperature "
    "and other factors. Model confidence is not clinical confidence."
)


def analysis_report(db: Session, user: User, analysis: AnalysisResult) -> Report:
    report = Report(
        user_id=user.id,
        kind="analysis",
        title=f"Analysis report — {analysis.title}",
        analysis_id=analysis.id,
        meta=json.dumps({"model_version": analysis.model_version}),
    )
    db.add(report)
    db.flush()

    pdf = _new_pdf()
    _title(
        pdf,
        "Physiological pattern analysis",
        f"{analysis.title}  |  Generated {datetime.now(timezone.utc).strftime('%d %b %Y %H:%M UTC')}",
    )
    _badge(
        pdf,
        analysis.predicted_label.upper(),
        CORAL if analysis.predicted_class == "stress" else AMBER if analysis.predicted_class is None else SAGE,
    )
    _kv(
        pdf,
        [
            ("Account", f"{user.name} ({user.role})"),
            ("Data provenance", analysis.source_label or analysis.source_type),
            ("Recorded", analysis.created_at.strftime("%d %b %Y %H:%M UTC") if analysis.created_at else "-"),
            ("Model", f"{analysis.model_version}"),
            ("Model confidence", f"{analysis.confidence:.0%}" if analysis.confidence is not None else "not reported"),
            ("Stress-associated probability", f"{analysis.stress_score:.1f}%" if analysis.stress_score is not None else "not reported"),
            ("Signal quality", f"{analysis.quality_score:.0f}/100 ({analysis.quality_grade})" if analysis.quality_score is not None else "not assessed"),
            ("Windows analysed", f"{analysis.window_count} window(s), {analysis.duration_seconds:.0f}s"),
        ],
    )

    _h2(pdf, "What this estimate means")
    _para(
        pdf,
        "The model compares the extracted features with three conditions represented in WESAD: neutral baseline, "
        "a stress condition and an amusement condition. The displayed class is the highest-probability class after "
        "aggregating the analysed windows.",
    )
    probabilities = json.loads(analysis.class_probabilities or "{}")
    if probabilities:
        pdf.ln(2)
        for name, value in sorted(probabilities.items(), key=lambda item: item[1], reverse=True):
            _bar(pdf, name.capitalize(), float(value), f"{float(value) * 100:.0f}%", FOREST if name != "stress" else AMBER)

    _h2(pdf, "Measured signal features")
    features = json.loads(analysis.features or "{}")
    try:
        explanation = json.loads(analysis.explanation or "{}")
    except json.JSONDecodeError:
        explanation = {}
    local = explanation.get("local", [])
    shown = local[:8] if local else []
    if shown:
        for item in shown:
            unit = item.get("unit") or ""
            _bar(
                pdf,
                f"{item.get('label')} ({item.get('value')} {unit})".strip(),
                min(1.0, abs(float(item.get("contribution", 0))) / 0.25),
                f"{float(item.get('contribution', 0)):+.3f}",
                SAGE if item.get("contribution", 0) >= 0 else CORAL,
            )
        _para(
            pdf,
            "Bars show occlusion contributions: the change in the predicted-class probability when a feature is "
            "set to its training median. Positive values pushed the prediction toward the displayed class. This "
            "describes model behaviour, not biological causation.",
            8.5,
            GREY,
        )
    else:
        _para(pdf, "No local attribution was available for this analysis.", 9, GREY)

    top_global = explanation.get("global_top", [])[:6]
    if top_global:
        _h2(pdf, "Model-level (global) feature importance")
        max_importance = max(float(item.get("share", 0)) for item in top_global) or 1.0
        for item in top_global:
            name = item.get("feature", "")
            label = FEATURE_META.get(name, {}).get("label", name)
            _bar(pdf, label, float(item.get("share", 0)) / max_importance, f"{float(item.get('share', 0)) * 100:.1f}%", SAGE)

    imputed = json.loads(analysis.imputed_features or "[]")
    if imputed:
        _h2(pdf, "Missing channels and imputed features")
        _para(
            pdf,
            "The following features were not measurable from this input and were replaced with the training "
            "median before inference. Treat the estimate with additional caution: "
            + ", ".join(FEATURE_META.get(name, {}).get("label", name) for name in imputed),
            9,
            CORAL,
        )

    _h2(pdf, "Suggested next steps for reviewing the data")
    _para(
        pdf,
        "1. Check sensor contact and recording length; repeat the recording if quality is below 60/100.\n"
        "2. Compare the feature values with your own baseline and with the reference medians above.\n"
        "3. Note movement, caffeine, sleep and recent activity, which can produce similar patterns.\n"
        "4. Treat a single window as exploratory; look for consistency across sessions.",
        9,
    )

    _h2(pdf, "Limitations and scientific disclaimer")
    _para(pdf, DISCLAIMER, 8.5, GREY)
    _para(
        pdf,
        "WESAD contains 15 laboratory participants following a fixed protocol. Participant-independent evaluation "
        "reduces identity leakage but does not establish generalisation to everyday life, other devices, or "
        "clinical populations. The model cannot determine whether you are stressed.",
        8.5,
        GREY,
    )

    report.file_path = _save(pdf, report)
    db.commit()
    db.refresh(report)
    return report


def research_report(
    db: Session, user: User, dataset: Dataset, metrics: dict, experiment: ResearchExperiment | None = None
) -> Report:
    report = Report(
        user_id=user.id,
        kind="research",
        title=f"Research evaluation — {dataset.name}",
        experiment_id=experiment.id if experiment else None,
        meta=json.dumps({"best_model": metrics.get("best_model"), "strategy": metrics.get("evaluation_strategy")}),
    )
    db.add(report)
    db.flush()

    pdf = _new_pdf()
    _title(pdf, "Model evaluation report", f"{dataset.name}  |  Generated {datetime.now(timezone.utc).strftime('%d %b %Y %H:%M UTC')}")
    _kv(
        pdf,
        [
            ("Dataset", dataset.name),
            ("Source", dataset.source),
            ("Participants", str(metrics.get("participants", dataset.participant_count))),
            ("Windows", str(metrics.get("windows", ""))),
            ("Evaluation", metrics.get("evaluation_strategy", "")),
            ("Selected model", metrics.get("best_model", "")),
            ("Generated by", f"{user.name} ({user.role})"),
        ],
    )
    _h2(pdf, "Dataset")
    _para(pdf, dataset.description or "No dataset description recorded.")
    if metrics.get("class_distribution"):
        pdf.ln(2)
        for name, count in metrics["class_distribution"].items():
            total = sum(metrics["class_distribution"].values()) or 1
            _bar(pdf, f"Class: {name}", float(count) / total, f"{count}")

    _h2(pdf, "Model comparison (participant-independent)")
    for result in metrics.get("models", []):
        m = result.get("metrics", {})
        _badge(
            pdf,
            result.get("model", "model"),
            FOREST if result.get("model") == metrics.get("best_model") else SAGE,
        )
        _kv(
            pdf,
            [
                ("Accuracy", f"{m.get('accuracy', 0):.3f}"),
                ("Balanced accuracy", f"{m.get('balanced_accuracy', 0):.3f}"),
                ("Macro precision", f"{m.get('precision_macro', 0):.3f}"),
                ("Macro recall", f"{m.get('recall_macro', 0):.3f}"),
                ("Macro F1", f"{m.get('f1_macro', 0):.3f}"),
                ("Mean subject balanced acc.", f"{result.get('mean_subject_balanced_accuracy', 0):.3f}"),
                ("Test windows", str(m.get("n_test_windows", ""))),
            ],
        )

    best = next((r for r in metrics.get("models", []) if r.get("model") == metrics.get("best_model")), None)
    if best and best.get("metrics", {}).get("confusion_matrix"):
        _h2(pdf, "Confusion matrix — selected model")
        _confusion(pdf, best["metrics"]["confusion_matrix"], metrics.get("classes", ["neutral", "stress", "amusement"]))
        _para(pdf, "Rows are the true WESAD condition; columns are predicted classes, summed across participant-independent folds.", 8.5, GREY)

    _h2(pdf, "Per-class performance")
    if best:
        _kv(
            pdf,
            [
                (
                    name,
                    f"precision {vals.get('precision', 0):.2f} | recall {vals.get('recall', 0):.2f} | "
                    f"F1 {vals.get('f1', 0):.2f} | support {vals.get('support', 0)}",
                )
                for name, vals in best.get("metrics", {}).get("per_class", {}).items()
            ],
        )

    importance = metrics.get("feature_importance", [])[:12]
    if importance:
        _h2(pdf, "Global feature importance (permutation, held-out participants)")
        max_share = max(float(item.get("share", 0)) for item in importance) or 1.0
        for item in importance:
            name = item.get("feature", "")
            _bar(pdf, FEATURE_META.get(name, {}).get("label", name), float(item.get("share", 0)) / max_share, f"{float(item.get('share', 0)) * 100:.1f}%", SAGE)

    subject_rows = list((best or {}).get("per_subject", {}).items())
    if subject_rows:
        _h2(pdf, "Per-participant results (selected model)")
        for subject, stats in subject_rows:
            _bar(pdf, subject, float(stats.get("balanced_accuracy", 0)), f"{float(stats.get('balanced_accuracy', 0)):.2f}", FOREST)
        _para(
            pdf,
            "Each participant was held out entirely during training for their evaluation fold. Scores vary "
            "considerably between participants, which is expected with 15 participants.",
            8.5,
            GREY,
        )

    _h2(pdf, "Limitations")
    for item in metrics.get("limitations", []):
        _para(pdf, f"- {item}", 8.5, GREY)
    _para(pdf, DISCLAIMER, 8.5, GREY)

    report.file_path = _save(pdf, report)
    db.commit()
    db.refresh(report)
    return report


def institution_report(db: Session, user: User, overview: dict) -> Report:
    report = Report(
        user_id=user.id,
        kind="institution",
        title=f"Aggregate insights — {datetime.now(timezone.utc).strftime('%d %b %Y')}",
        meta=json.dumps({"weeks": overview.get("window_weeks"), "min_cohort": overview.get("min_cohort")}),
    )
    db.add(report)
    db.flush()

    pdf = _new_pdf()
    _title(pdf, "Aggregate physiological insights", "Privacy-preserving institutional summary")
    summary = overview.get("summary", {})
    _kv(
        pdf,
        [
            ("Sessions included", str(summary.get("sessions", 0))),
            ("Participants", str(summary.get("participants", 0))),
            ("Opted-in users", str(summary.get("consenting_users", 0))),
            ("Mean stress-associated probability", f"{summary.get('mean_stress_probability')}%"),
            ("Mean signal quality", f"{summary.get('mean_quality')}/100"),
            ("Minimum cohort", f"{overview.get('min_cohort')} sessions"),
            ("Suppressed groups", str(overview.get("privacy", {}).get("suppressed_groups", 0))),
        ],
    )
    _h2(pdf, "Weekly aggregates")
    for row in overview.get("weekly", []):
        _para(
            pdf,
            f"Week of {row['week_start']}: {row['sessions']} sessions from {row['participants']} participants; "
            f"stress-associated share {row['stress_share']}%; mean quality {row['mean_quality']}/100.",
            9,
        )
    if not overview.get("weekly"):
        _para(pdf, "No group met the minimum cohort size, so no weekly aggregate is shown.", 9, GREY)

    _h2(pdf, "Privacy statement")
    _para(pdf, overview.get("privacy", {}).get("note", ""), 8.5, GREY)
    _para(pdf, overview.get("disclaimer", ""), 8.5, GREY)
    _para(pdf, "This report must not be used for student or employee surveillance, performance evaluation or clinical decisions.", 8.5, CORAL)

    report.file_path = _save(pdf, report)
    db.commit()
    db.refresh(report)
    return report
