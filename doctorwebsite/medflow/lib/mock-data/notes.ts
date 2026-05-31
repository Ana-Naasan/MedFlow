import type { Note } from "@/lib/types";

export const notes: Note[] = [
  // ─── Margaret Chen (10231) ───────────────────────────────────────────────────
  {
    id: "note-005",
    patientId: "10231",
    date: "2024-02-08",
    author: "Chen, James",
    title: "Metformin dose escalation",
    content:
      "Metformin increased from 500mg BID to 1000mg BID following suboptimal HbA1c (7.8%). Patient counselled on GI side effects (nausea, diarrhea) — advised to take with food and titrate gradually. Reviewed contraindications: eGFR currently 62, within acceptable range for Metformin use. Will hold if eGFR drops below 45. Repeat HbA1c in 3 months.",
    tags: ["prescription", "clinical"],
    lastEditedAt: "2024-02-08T11:00:00",
  },
  {
    id: "note-006",
    patientId: "10231",
    date: "2024-08-15",
    author: "Chen, James",
    title: "Overdue immunizations — flu and pneumococcal",
    content:
      "Influenza vaccine and Pneumovax 23 both overdue. Patient declined flu vaccine last year due to perceived side effects. Education provided on influenza severity risk in elderly diabetic patients. Patient agreed to receive both vaccines today. Influenza QIV-HD administered IM left deltoid. Pneumovax 23 administered IM right deltoid. No adverse reactions observed post-administration. POPHIS submitted.",
    tags: ["admin", "clinical"],
    lastEditedAt: "2024-08-15T12:00:00",
  },
  {
    id: "note-007",
    patientId: "10231",
    date: "2024-05-20",
    author: "Chen, James",
    title: "Telehealth — orthostatic hypotension assessment",
    content:
      "Patient reports dizziness and lightheadedness on standing, particularly on waking. Symptoms started after Lisinopril dose last adjusted. BP diary shows readings ranging 110–130/70–80 at rest. No falls to date. Advised to rise slowly and in stages, increase fluid intake to 1.5–2L/day, avoid hot environments. Lisinopril dose not changed at this time. If BP consistently below 110 systolic, will reassess dose. Home readings requested x 2 weeks.",
    tags: ["clinical"],
    lastEditedAt: "2024-05-20T14:30:00",
  },
  {
    id: "note-008",
    patientId: "10231",
    date: "2024-08-15",
    author: "Admin Staff",
    title: "Referral sent — ophthalmology (diabetic eye exam)",
    content:
      "Referral letter faxed to Dr. P. Okafor, Ophthalmology, on 2024-08-16. Confirmed received. Patient advised appointment will be within 3 months. Contact information provided. Chart flagged for follow-up if no appointment confirmed within 8 weeks.",
    tags: ["admin", "referral"],
    lastEditedAt: "2024-08-16T09:15:00",
  },

  // ─── Raj Patel (33591) ───────────────────────────────────────────────────────
  {
    id: "note-009",
    patientId: "33591",
    date: "2023-08-14",
    author: "Wu, Bella",
    title: "MDD diagnosis — initial assessment and safety plan",
    content:
      "Patient presents with 3-month history of low mood, anhedonia, sleep disturbance, and poor concentration. PHQ-9 = 17 (moderately severe). Safety assessment completed: no active suicidal ideation, no plan or intent. Emergency contacts identified (spouse, Priya Patel). Crisis line number provided (Crisis Support Centre Calgary: 403-266-4357). Sertraline 50mg initiated. Return in 6 weeks or sooner if symptoms worsen or SI develops.",
    tags: ["clinical"],
    lastEditedAt: "2023-08-14T10:30:00",
  },
  {
    id: "note-010",
    patientId: "33591",
    date: "2024-03-05",
    author: "Wu, Bella",
    title: "Referral — clinical psychology (CBT for MDD)",
    content:
      "Referral to Dr. T. Larsson, Clinical Psychologist, placed for 8-session CBT program. Rationale: good pharmacological response to Sertraline (PHQ-9 down to 9) but residual anhedonia and functional impairment. CBT targeting negative automatic thoughts and behavioural activation. Patient agreeable. Direct referral sent via fax — expected wait 4–6 weeks. Follow up in 3 months.",
    tags: ["referral", "clinical"],
    lastEditedAt: "2024-03-05T13:45:00",
  },
  {
    id: "note-011",
    patientId: "33591",
    date: "2024-06-18",
    author: "Wu, Bella",
    title: "Pantoprazole initiated — GERD management",
    content:
      "Patient reports recurrence of heartburn and regurgitation, worsening over 3 weeks. Symptoms occurring nightly despite dietary modification (low-fat diet, no caffeine, no late meals). Pantoprazole 40mg daily before breakfast initiated. Advised to elevate head of bed 15–20 cm. Avoid NSAIDs. If symptoms persist beyond 4 weeks on PPI, GI referral (already pending) to proceed with upper endoscopy.",
    tags: ["prescription", "clinical"],
    lastEditedAt: "2024-06-18T15:00:00",
  },
  {
    id: "note-012",
    patientId: "33591",
    date: "2024-09-22",
    author: "Admin Staff",
    title: "Appointment reminder — annual review booked",
    content:
      "Annual review appointment booked for 2024-09-22 at 14:00. Patient confirmed via phone. Reminder sent via patient portal. Requisition for fasting bloodwork (TSH, LFTs) sent to LifeLabs prior to appointment. Patient advised to arrive fasting.",
    tags: ["admin"],
    lastEditedAt: "2024-09-15T10:00:00",
  },

  // ─── Sophie Dubois (57720) ───────────────────────────────────────────────────
  {
    id: "note-013",
    patientId: "57720",
    date: "2023-09-06",
    author: "Wu, Bella",
    title: "Post-anaphylaxis follow-up plan",
    content:
      "Patient discharged from ER stable following anaphylaxis from accidental tree nut ingestion at a restaurant. Follow-up planned within 1 week. Review EpiPen technique with patient and family. Discuss anaphylaxis management plan and restaurant safety protocols. Medic Alert bracelet strongly recommended — patient agrees to purchase. Refer to allergist for formal desensitization workup.",
    tags: ["clinical"],
    lastEditedAt: "2023-09-06T09:30:00",
  },
  {
    id: "note-014",
    patientId: "57720",
    date: "2024-04-11",
    author: "Wu, Bella",
    title: "Eczema management plan — moderate flare",
    content:
      "Eczema flare on bilateral forearms and posterior neck, lichenified plaques without secondary infection. Initiated Hydrocortisone 1% cream BID x 2 weeks. Reinforced emollient use: Cetaphil Moisturizing Cream applied daily after bathing. Discussed trigger avoidance: fragrance-free products, avoid wool fabrics, manage stress. If no improvement in 4 weeks, refer to dermatology for consideration of stronger topical corticosteroid or Dupilumab assessment.",
    tags: ["clinical", "prescription"],
    lastEditedAt: "2024-04-11T11:30:00",
  },
  {
    id: "note-015",
    patientId: "57720",
    date: "2024-07-30",
    author: "Admin Staff",
    title: "EpiPen renewal — prescription faxed to pharmacy",
    content:
      "EpiPen 0.3mg auto-injector renewed x2. Prescription faxed to Shoppers Drug Mart Sherwood Park. Patient advised to ensure one EpiPen is always carried and one stored at home. Expiry checked — patient's previous EpiPen expired June 2024. Pharmacist notified to counsel on auto-injector use at dispensing. New prescription valid 12 months.",
    tags: ["prescription", "admin"],
    lastEditedAt: "2024-07-30T11:00:00",
  },
  {
    id: "note-016",
    patientId: "57720",
    date: "2024-07-30",
    author: "Wu, Bella",
    title: "Allergist referral — OIT consideration",
    content:
      "Patient and mother expressed interest in oral immunotherapy (OIT) for tree nut desensitization. Discussed candidacy: suitable candidate given controlled atopic dermatitis, stable baseline, and motivation. Referred to Dr. M. Ng, allergist, Edmonton. Expected wait time 3–6 months. Family counselled on realistic expectations: OIT is not a cure and lifelong EpiPen carry will remain necessary.",
    tags: ["referral", "clinical"],
    lastEditedAt: "2024-07-30T11:45:00",
  },

  // ─── Gerald Morrison (68103) ─────────────────────────────────────────────────
  {
    id: "note-017",
    patientId: "68103",
    date: "2024-01-22",
    author: "Chen, James",
    title: "Heart failure — fluid management and diuretic adjustment",
    content:
      "Patient presents with 2 kg weight gain and 1+ pitting ankle edema — consistent with mild fluid overload. Furosemide increased from 40mg to 80mg daily x 2 weeks, then return to 40mg maintenance. Patient instructed on daily weight monitoring: if weight increases >2 kg over 24 hours, contact clinic same day or proceed to ER. Sodium intake reviewed — patient reports compliance with <2000 mg/day sodium diet. Electrolytes to be checked in 1 week.",
    tags: ["clinical", "prescription"],
    lastEditedAt: "2024-01-22T09:45:00",
  },
  {
    id: "note-018",
    patientId: "68103",
    date: "2024-04-03",
    author: "Chen, James",
    title: "Cardiology recommendations — SGLT2 inhibitor initiation",
    content:
      "Following cardiology review (Dr. R. Kapoor), recommendation to add Empagliflozin 10mg daily for HFrEF mortality benefit and secondary diabetes management. eGFR 38 — within range for initiation (threshold ≥20 mL/min for HF indication). Patient counselled on risk of DKA (rare), urinary infections, and genital mycotic infections. Consent documented. Empagliflozin 10mg prescribed. Renal function to be rechecked in 4 weeks.",
    tags: ["clinical", "prescription"],
    lastEditedAt: "2024-04-05T14:00:00",
  },
  {
    id: "note-019",
    patientId: "68103",
    date: "2024-07-15",
    author: "Chen, James",
    title: "Warfarin management — supratherapeutic INR 3.8",
    content:
      "INR 3.8 — above therapeutic target of 2.0–3.0. No evidence of active bleeding. Likely cause: significant increase in dietary vitamin K (leafy greens) over past 2 weeks. Warfarin held for 1 dose then restarted at 4mg daily (reduced from 5mg). Patient counselled to maintain consistent vitamin K intake rather than avoidance — emphasised consistency is key. Repeat INR in 1 week. If still >3.5 or bleeding occurs, contact clinic urgently.",
    tags: ["clinical"],
    lastEditedAt: "2024-07-15T11:30:00",
  },
  {
    id: "note-020",
    patientId: "68103",
    date: "2024-09-05",
    author: "Admin Staff",
    title: "Chest X-ray requisition — patient directed to imaging centre",
    content:
      "Requisition for portable chest X-ray generated and given to patient. Directed to Alberta Health Services Radiology, Leduc Community Hospital. Patient unable to travel to Edmonton today. Advised results will be available to Dr. Chen within 48–72 hours via Netcare. If dyspnea worsens acutely before results available, patient advised to call 911.",
    tags: ["admin"],
    lastEditedAt: "2024-09-05T12:15:00",
  },

  // ─── Harold Whitmore (24884) ─────────────────────────────────────────────────
  {
    id: "note-hw-001",
    patientId: "24884",
    date: "2010-09-15",
    author: "Park, Eleanor",
    title: "Initial H&P — New Patient (Establishing Care)",
    content:
      "<p>65-year-old retired postal supervisor establishing primary care after relocation. Requests a full check-up. No acute complaints.</p><h2>History of Present Illness</h2><p>Mild exertional fatigue climbing two flights of stairs; no chest pain, orthopnea, or edema. Borderline-high BP noted at pharmacy screenings over the past two years, never treated. ~7 kg weight gain over 5 years. Increased thirst and nocturia (×2–3) over recent months; no polyuria, visual change, or weight loss.</p><h2>Past Medical / Surgical</h2><p>Borderline hypertension (untreated). Appendectomy at age 22. No prior hospitalizations otherwise. No known diabetes or coronary disease.</p><h2>Social History</h2><p>~1 pack/day since age 25 (≈40 pack-years), currently smoking. Alcohol 3–4 beers/week. Retired, lives with spouse, sedentary.</p><h2>Family History</h2><p>Father — MI at 68. Mother — type 2 diabetes. Brother — prostate cancer at 74.</p><h2>Assessment</h2><ul><li>Hypertension, Stage 2 — newly confirmed in clinic (158/94)</li><li>Suspected impaired glucose metabolism — screen for diabetes</li><li>Dyslipidemia — to characterize</li><li>Tobacco use disorder, ~40 pack-years — active</li><li>Obesity (BMI 31.4)</li></ul><h2>Plan</h2><p>Fasting labs ordered (CBC, CMP, HbA1c, lipid panel, TSH, UA). In-clinic ECG normal sinus rhythm. Start lisinopril 10 mg daily with home BP log. Smoking cessation counseling and NRT offered. DASH diet, 150 min/week activity, weight loss. Return in 4 weeks.</p>",
    tags: ["clinical"],
    lastEditedAt: "2010-09-15T11:30:00",
  },
  {
    id: "note-hw-002",
    patientId: "24884",
    date: "2010-10-13",
    author: "Park, Eleanor",
    title: "Pre-diabetes counseling & lipid management",
    content:
      "<p>Fasting labs reviewed at 4-week follow-up. HbA1c 6.1% confirms pre-diabetes. Lipid panel shows LDL 172 mg/dL, HDL 38, triglycerides 210 — consistent with dyslipidemia.</p><p>BP improved to 142/88 on lisinopril 10 mg. Atorvastatin 20 mg nightly initiated for dyslipidemia. Reinforced DASH-style diet, weight loss target, and physical activity. Smoking cessation discussed again — patient still considering NRT. Repeat HbA1c and lipids planned at next annual review.</p>",
    tags: ["clinical"],
    lastEditedAt: "2010-10-13T10:30:00",
  },
  {
    id: "note-hw-003",
    patientId: "24884",
    date: "2014-11-10",
    author: "Park, Eleanor",
    title: "Type 2 diabetes diagnosis — Metformin initiation",
    content:
      "<p>HbA1c 7.2% crosses the diagnostic threshold for type 2 diabetes mellitus. Patient reports worsening nocturia and persistent fatigue; weight up to 98.2 kg.</p><p>Started metformin 500 mg BID with meals, to uptitrate to 1000 mg BID over 4 weeks as tolerated. Counseled on GI side effects and to take with food. Atorvastatin increased to 40 mg nightly for LDL above target. Diabetes education referral placed; home glucose monitoring initiated. Notably, patient quit smoking in 2013 — nicotine dependence marked resolved. Baseline diabetic foot exam intact. Repeat HbA1c in 3 months.</p>",
    tags: ["clinical", "prescription"],
    lastEditedAt: "2014-11-10T11:00:00",
  },
  {
    id: "note-hw-004",
    patientId: "24884",
    date: "2018-07-08",
    author: "Admin Staff",
    title: "Ophthalmology referral — diabetic eye exam",
    content:
      "<p>Referral faxed to Springfield Eye Associates for annual diabetic retinopathy screening. Patient advised appointment will be within 6–8 weeks. Chart flagged for follow-up if not booked within 4 weeks. PSA discussion documented separately — value 3.2 with normal DRE, watchful waiting.</p>",
    tags: ["admin", "referral"],
    lastEditedAt: "2018-07-08T13:00:00",
  },
  {
    id: "note-hw-005",
    patientId: "24884",
    date: "2026-03-08",
    author: "Park, Eleanor",
    title: "Annual review — glycemic target revision",
    content:
      "<p>Annual review. HbA1c 7.4% — slightly above target. BP 130/80 on current regimen. Encouraging weight loss to 94.1 kg from a peak of 99 kg. eGFR 66 (CKD stage 2, stable).</p><p>Discussed adding empagliflozin 10 mg daily given combined cardiac (HFpEF risk, mild LVH) and renal protective benefit, plus modest glycemic improvement. Patient will consider and decide at follow-up. Continue lisinopril, metformin, atorvastatin, bisoprolol, and ASA. Reinforced diet and activity. Repeat HbA1c and renal panel in 3 months; continue annual diabetic eye and foot screening.</p>",
    tags: ["clinical"],
    lastEditedAt: "2026-03-08T11:00:00",
  },
];

export function getNotesByPatientId(patientId: string): Note[] {
  return notes.filter((n) => n.patientId === patientId);
}

export function getNoteById(id: string): Note | undefined {
  return notes.find((n) => n.id === id);
}
