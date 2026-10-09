"""
Compile all validation work (original pooled, Deep Haven-only, leakage
correction, and final multi-point results) into a single PDF report.
"""
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image, HRFlowable
)

PROJECT_DIR = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_DIR / "output"
PDF_PATH = OUT_DIR / "Squam_Water_Clarity_Validation_Report.pdf"

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="SectionHeading", fontSize=16, leading=20, spaceBefore=18,
                           spaceAfter=8, textColor=colors.HexColor("#1a3a5c"), fontName="Helvetica-Bold"))
styles.add(ParagraphStyle(name="SubHeading", fontSize=12, leading=15, spaceBefore=12,
                           spaceAfter=6, fontName="Helvetica-Bold", textColor=colors.HexColor("#333333")))
styles.add(ParagraphStyle(name="BodyJustify", parent=styles["Normal"], fontSize=10, leading=14, spaceAfter=8))
styles.add(ParagraphStyle(name="Caption", parent=styles["Normal"], fontSize=8.5, leading=11,
                           textColor=colors.HexColor("#555555"), spaceAfter=12))
styles.add(ParagraphStyle(name="TitleMain", fontSize=22, leading=26, alignment=1,
                           fontName="Helvetica-Bold", textColor=colors.HexColor("#1a3a5c"), spaceAfter=6))
styles.add(ParagraphStyle(name="SubtitleMain", fontSize=12, leading=16, alignment=1,
                           textColor=colors.HexColor("#555555"), spaceAfter=24))

TABLE_HEADER_BG = colors.HexColor("#1a3a5c")
TABLE_ALT_BG = colors.HexColor("#f2f5f8")


def make_table(header, rows, col_widths=None):
    data = [header] + rows
    t = Table(data, colWidths=col_widths, hAlign="LEFT")
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), TABLE_HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), TABLE_ALT_BG))
    t.setStyle(TableStyle(style))
    return t


def make_image(path, max_width=6.3 * inch, max_height=4.6 * inch):
    from PIL import Image as PILImage
    with PILImage.open(path) as im:
        w, h = im.size
    ratio = min(max_width / w, max_height / h)
    return Image(str(path), width=w * ratio, height=h * ratio)


def build():
    story = []

    # --- Title page ---
    story.append(Spacer(1, 1.5 * inch))
    story.append(Paragraph("Squam Lake Water Clarity Model", styles["TitleMain"]))
    story.append(Paragraph("Validation Report: Compiled Results Across Four Rounds of Testing", styles["SubtitleMain"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cccccc")))
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph(
        "This report compiles every validation pass run against real in-lake Secchi depth readings for "
        "Squam Lake and Little Squam Lake, NH, in the order they were performed: the original pooled "
        "lake-wide comparison, a Deep Haven-only comparison testing whether averaging across Squam's many "
        "bays was diluting a real signal, a correction after discovering the production model had partly "
        "trained on Squam-area data, and a final multi-point comparison matching each real reading to a "
        "prediction from its own specific monitoring site. All correlations are compared against the "
        "national LAGOS-US LANDSAT model's baseline of r = -0.12 (p = 0.52, n = 29) at these lakes, which is what "
        "motivated this project in the first place.",
        styles["BodyJustify"]
    ))
    story.append(PageBreak())

    # =====================================================================
    # SECTION 1: Original pooled results
    # =====================================================================
    story.append(Paragraph("1. Original Pooled Validation Results", styles["SectionHeading"]))
    story.append(Paragraph(
        "The first validation pass compared model predictions at one central coordinate per lake against "
        "real Secchi readings averaged across all reporting stations on each lake, for each date. "
        "National model baseline at these lakes: r = -0.12, p = 0.52, n = 29 (no real relationship).",
        styles["BodyJustify"]
    ))

    story.append(Paragraph("Exact date match", styles["SubHeading"]))
    story.append(make_table(
        ["Comparison", "n", "Pearson r", "p-value", "R2", "MAE (m)", "RMSE (m)"],
        [
            ["Both lakes pooled", "23", "0.061", "0.7833", "0.004", "1.816", "2.200"],
            ["Squam Lake only", "14", "-0.164", "0.5747", "0.027", "1.902", "2.394"],
            ["Little Squam Lake only", "9", "0.349", "0.3574", "0.122", "1.682", "1.858"],
        ]
    ))

    story.append(Paragraph("+/-3-day tolerance match", styles["SubHeading"]))
    story.append(make_table(
        ["Comparison", "n", "Pearson r", "p-value", "R2", "MAE (m)", "RMSE (m)"],
        [
            ["Both lakes pooled", "97", "0.212", "0.0373", "0.045", "1.909", "2.253"],
            ["Squam Lake only", "52", "0.175", "0.2155", "0.031", "1.765", "2.155"],
            ["Little Squam Lake only", "45", "0.271", "0.0720", "0.073", "2.076", "2.361"],
        ]
    ))
    story.append(Spacer(1, 10))
    story.append(make_image(OUT_DIR / "validation_scatter.png"))
    story.append(Paragraph(
        "Figure 1. Predicted vs. real Secchi depth, both lakes pooled at their central coordinates, "
        "+/-3-day tolerance match.", styles["Caption"]
    ))
    story.append(PageBreak())

    # =====================================================================
    # SECTION 2: Deep Haven only
    # =====================================================================
    story.append(Paragraph("2. Deep Haven-Only Results", styles["SectionHeading"]))
    story.append(Paragraph(
        "Squam Lake is a large, multi-basin lake, and the real-readings file showed many stations sampled "
        "on the same date -- averaging across all of them could dilute a real, localized signal. This pass "
        "restricted Squam's comparison to a single consistent monitoring site, Deep Haven, while leaving "
        "Little Squam's comparison unchanged (lake-wide average, only one site available for that lake).",
        styles["BodyJustify"]
    ))

    story.append(Paragraph("Exact date match", styles["SubHeading"]))
    story.append(make_table(
        ["Comparison", "n", "Pearson r", "p-value", "R2", "MAE (m)", "RMSE (m)"],
        [
            ["All (Squam/Deep Haven + Little Squam)", "21", "0.202", "0.3791", "0.041", "2.177", "2.519"],
            ["Squam Lake (Deep Haven only)", "12", "0.089", "0.7832", "0.008", "2.548", "2.918"],
            ["Little Squam Lake (unchanged)", "9", "0.349", "0.3574", "0.122", "1.682", "1.858"],
        ]
    ))

    story.append(Paragraph("+/-3-day tolerance match", styles["SubHeading"]))
    story.append(make_table(
        ["Comparison", "n", "Pearson r", "p-value", "R2", "MAE (m)", "RMSE (m)"],
        [
            ["All, tolerance", "86", "0.312", "0.0035", "0.097", "2.377", "2.692"],
            ["Squam Lake (Deep Haven only)", "41", "0.323", "0.0392", "0.105", "2.708", "3.014"],
            ["Little Squam Lake (unchanged)", "45", "0.271", "0.0720", "0.073", "2.076", "2.361"],
        ]
    ))
    story.append(Spacer(1, 10))
    story.append(make_image(OUT_DIR / "validation_scatter_deephaven.png"))
    story.append(Paragraph(
        "Figure 2. Predicted vs. real Secchi depth, Squam restricted to the Deep Haven site, "
        "+/-3-day tolerance match. Correlation improved for Squam under the looser tolerance match, but "
        "absolute error (MAE) got worse, not better -- a partial, not a confirming, result.", styles["Caption"]
    ))
    story.append(PageBreak())

    # =====================================================================
    # SECTION 3: Leakage correction
    # =====================================================================
    story.append(Paragraph("3. Data Leakage Correction", styles["SectionHeading"]))
    story.append(Paragraph(
        "A review of the training data found that 107 rows, drawn from 16 monitoring sites, were genuine "
        "Squam Lake and Little Squam Lake stations (the same NH DES monitoring network used in the real "
        "validation data, e.g. \"SQUAM LAKE-DEEP HAVEN\", \"SQUAM LAKE-LOON REEF\") included in the pool "
        "of ~19,500 rows used to train the production model. The spatial cross-validation figure reported "
        "during model development (r = 0.512, testing on entirely unseen lakes) remained valid, since it "
        "used group-based cross-validation that held out whole lakes in rotation. But the single final "
        "model used to generate the actual Squam/Little Squam predictions had been trained on all rows, "
        "including these 107 -- meaning the validation comparisons above were not fully independent tests "
        "for the overlapping records.",
        styles["BodyJustify"]
    ))
    story.append(Paragraph(
        "The model was retrained excluding every Squam-area site entirely (19,403 rows, 1,383 sites "
        "remaining). Spatial cross-validation on this reduced pool was nearly identical to before "
        "(r = 0.507 vs. 0.512), indicating the excluded rows had negligible influence on the model overall "
        "-- but the corrected model is the only one that has genuinely never seen Squam or Little Squam "
        "data, so it is the valid one for the remaining comparisons in this report.",
        styles["BodyJustify"]
    ))

    story.append(Paragraph("Corrected: Exact date match", styles["SubHeading"]))
    story.append(make_table(
        ["Comparison", "n", "Pearson r", "p-value", "R2", "MAE (m)", "RMSE (m)"],
        [
            ["Both lakes pooled (lake-wide)", "23", "0.112", "0.6100", "0.013", "1.799", "2.177"],
            ["Squam Lake only (lake-wide)", "14", "-0.123", "0.6758", "0.015", "1.895", "2.388"],
            ["Little Squam Lake only", "9", "0.432", "0.2453", "0.187", "1.650", "1.801"],
            ["Squam Lake (Deep Haven only)", "12", "0.130", "0.6879", "0.017", "2.485", "2.872"],
        ]
    ))

    story.append(Paragraph("Corrected: +/-3-day tolerance match", styles["SubHeading"]))
    story.append(make_table(
        ["Comparison", "n", "Pearson r", "p-value", "R2", "MAE (m)", "RMSE (m)"],
        [
            ["Both lakes pooled (lake-wide)", "97", "0.235", "0.0207", "0.055", "1.907", "2.243"],
            ["Squam Lake only (lake-wide)", "52", "0.194", "0.1678", "0.038", "1.785", "2.169"],
            ["Little Squam Lake only", "45", "0.302", "0.0438", "0.091", "2.048", "2.326"],
            ["Squam Lake (Deep Haven only)", "41", "0.335", "0.0323", "0.112", "2.707", "3.017"],
        ]
    ))
    story.append(Spacer(1, 10))
    story.append(make_image(OUT_DIR / "validation_scatter_heldout.png"))
    story.append(Paragraph(
        "Figure 3a. Corrected model, lake-wide comparison, +/-3-day tolerance match.", styles["Caption"]
    ))
    story.append(Spacer(1, 10))
    story.append(make_image(OUT_DIR / "validation_scatter_deephaven_heldout.png"))
    story.append(Paragraph(
        "Figure 3b. Corrected model, Squam restricted to Deep Haven, +/-3-day tolerance match.",
        styles["Caption"]
    ))
    story.append(PageBreak())

    # =====================================================================
    # SECTION 4: Multi-point
    # =====================================================================
    story.append(Paragraph("4. Final Multi-Point Spatial Results", styles["SectionHeading"]))
    story.append(Paragraph(
        "The final validation pass used real GPS coordinates for 13 named monitoring sites across Squam "
        "and Little Squam, extracting a separate Landsat-based prediction at each site (instead of one "
        "central point per lake), and matching each real reading to the prediction from its own site using "
        "the site labels already present in the real-readings data. Predictions used the corrected, "
        "Squam-excluded model. Eight real-data site names had no matching coordinate provided and were "
        "excluded rather than guessed at: 1 East, 13 Bean Cove, 14 Strutevant Bay, 14A Inner Sturtevant "
        "Bay, 16A Inner Dog Cove, 1B, 20 Bear Cove, 9B Outer Squaw Cove.",
        styles["BodyJustify"]
    ))

    story.append(Paragraph("Pooled across all 13 matched sites", styles["SubHeading"]))
    story.append(make_table(
        ["Match type", "n", "Pearson r", "p-value", "R2", "MAE (m)", "RMSE (m)"],
        [
            ["Exact date", "135", "0.191", "0.0268", "0.036", "1.898", "2.318"],
            ["+/-3-day tolerance", "445", "0.264", "<0.0001", "0.070", "1.908", "2.292"],
        ]
    ))

    story.append(Paragraph("Per-site breakdown (+/-3-day tolerance match)", styles["SubHeading"]))
    story.append(make_table(
        ["Site", "n", "Pearson r", "p-value", "R2", "MAE (m)"],
        [
            ["5 Livermore Cove", "37", "0.463", "0.0039", "0.215", "1.623"],
            ["2 Cotton Cove", "29", "0.344", "0.0676", "0.118", "1.123"],
            ["8 Rattlesnake Cove", "32", "0.317", "0.0774", "0.100", "1.073"],
            ["9A Inner Squaw Cove", "25", "0.266", "0.1979", "0.071", "1.082"],
            ["12 Moultonboro Bay", "38", "0.224", "0.1757", "0.050", "2.159"],
            ["10 Sandwich Bay", "39", "0.204", "0.2125", "0.042", "2.699"],
            ["Deep Haven", "41", "0.186", "0.2451", "0.034", "2.773"],
            ["1 West (Little Squam)", "52", "0.165", "0.2423", "0.027", "2.029"],
            ["16 Dog Cove", "33", "0.143", "0.4266", "0.021", "1.259"],
            ["Loon Reef", "36", "0.146", "0.3966", "0.021", "2.885"],
            ["18 Piper Cove", "44", "0.119", "0.4420", "0.014", "1.447"],
            ["14 Sturtevant Bay", "37", "0.101", "0.5503", "0.010", "2.093"],
            ["11 Kent Island", "2", "—", "too few pairs", "—", "—"],
        ],
        col_widths=[1.7 * inch, 0.5 * inch, 0.8 * inch, 0.9 * inch, 0.6 * inch, 0.9 * inch]
    ))
    story.append(Spacer(1, 10))
    story.append(make_image(OUT_DIR / "validation_scatter_multipoint.png", max_width=6.0 * inch, max_height=5.2 * inch))
    story.append(Paragraph(
        "Figure 4. Per-site predictions vs. real readings, all 13 matched sites, +/-3-day tolerance match. "
        "Coves and nearshore sites (Livermore, Rattlesnake, Cotton) show the strongest, lowest-error "
        "relationships; the two open-water sites (Deep Haven, Loon Reef) show the weakest correlation "
        "and the largest errors.", styles["Caption"]
    ))
    story.append(PageBreak())

    # =====================================================================
    # Repo section
    # =====================================================================
    story.append(Paragraph("Code and Data", styles["SectionHeading"]))
    story.append(Paragraph(
        "All code, prediction outputs, and validation reports for this project are available at:",
        styles["BodyJustify"]
    ))
    story.append(Paragraph(
        '<link href="https://github.com/fgajarsa-sudo/squam-water-clarity-model" color="blue">'
        "https://github.com/fgajarsa-sudo/squam-water-clarity-model</link>",
        ParagraphStyle(name="Link", parent=styles["BodyJustify"], fontSize=11, textColor=colors.blue)
    ))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "The repository contains the full processing pipeline (12 numbered Python scripts covering data "
        "collection from the EPA Water Quality Portal, Landsat matching via Google Earth Engine, feature "
        "engineering, model training with spatial hold-out cross-validation, prediction generation, and "
        "all four rounds of validation described in this report), the final prediction CSVs/Excel files "
        "for Squam and Little Squam (1984-present), and every validation report and scatter plot referenced "
        "above. Raw and intermediate data files are intentionally excluded (large, reproducible from the "
        "public EPA and Earth Engine APIs, and some raw EPA fields contained incidental volunteer field "
        "notes unrelated to this project that were stripped before publication).",
        styles["BodyJustify"]
    ))

    doc = SimpleDocTemplate(
        str(PDF_PATH), pagesize=letter,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        title="Squam Lake Water Clarity Model - Validation Report",
        author="Squam Lake Water Clarity Project",
    )
    doc.build(story)
    print(f"Saved PDF to {PDF_PATH}")


if __name__ == "__main__":
    build()
