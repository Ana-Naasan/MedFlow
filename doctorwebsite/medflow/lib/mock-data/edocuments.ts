import type { EDocument } from "@/lib/types";

export const eDocuments: EDocument[] = [
  // ─── Margaret Chen (10231) ───────────────────────────────────────────────────
  {
    id: "edoc-004",
    patientId: "10231",
    date: "2024-02-10",
    docType: "lab-report",
    sender: "LifeLabs Edmonton",
    recipient: "Chen, James — Family Practice, Edmonton",
    status: "received",
    subject: "Lab Results — HbA1c, Fasting Lipids, CMP (10231)",
    content:
      "PATIENT: Margaret Chen | DOB: 1942-08-15 | REQUISITION: 10231-MET-240208\n\nHbA1c: 7.8% (H — target <8%)\nFasting Glucose: 9.1 mmol/L (H)\nLDL Cholesterol: 2.4 mmol/L\nHDL Cholesterol: 1.3 mmol/L\nTriglycerides: 1.8 mmol/L\nCreatinine: 88 umol/L | eGFR: 62 mL/min/1.73m2\nSodium: 139 mmol/L | Potassium: 4.1 mmol/L\nALT: 22 U/L | AST: 19 U/L",
    faxNumber: "780-458-2200",
  },
  {
    id: "edoc-005",
    patientId: "10231",
    date: "2024-08-16",
    docType: "referral-letter",
    sender: "Chen, James — Family Practice, Edmonton",
    recipient: "Dr. P. Okafor — Ophthalmology, Edmonton",
    status: "sent",
    subject: "Referral — Diabetic Retinopathy Screening (Margaret Chen)",
    content:
      "Dear Dr. Okafor,\n\nI am referring Margaret Chen (DOB: 1942-08-15, HN: 10231-6542) for her annual diabetic retinopathy screening. Mrs. Chen has had Type 2 diabetes mellitus (E11.9) since 2019, currently managed with Metformin 1000mg BID. She is overdue for ophthalmologic review by 18 months. No known ocular symptoms at this time.\n\nThank you for your assistance.\nDr. James Chen",
    faxNumber: "780-423-6600",
  },
  {
    id: "edoc-006",
    patientId: "10231",
    date: "2024-08-15",
    docType: "consent-form",
    sender: "Chen, James — Family Practice, Edmonton",
    recipient: "Margaret Chen",
    status: "received",
    subject: "Consent for Annual Flu and Pneumococcal Vaccination",
    content:
      "I, Margaret Chen, consent to receive the following vaccines on 2024-08-15:\n1. Influenza vaccine (QIV-HD, high-dose formulation for age 65+)\n2. Pneumococcal vaccine (Pneumovax 23)\n\nI have been informed of the benefits and potential side effects including local injection site reactions, low-grade fever, and rare severe allergic reactions. I have had the opportunity to ask questions.\n\nSigned: Margaret Chen | Witnessed by: Dr. James Chen",
  },

  // ─── Raj Patel (33591) ───────────────────────────────────────────────────────
  {
    id: "edoc-007",
    patientId: "33591",
    date: "2024-03-05",
    docType: "referral-letter",
    sender: "Wu, Bella — Family Practice, Calgary",
    recipient: "Dr. T. Larsson — Clinical Psychology, Calgary",
    status: "sent",
    subject: "Referral for CBT — Major Depressive Disorder (Raj Patel)",
    content:
      "Dear Dr. Larsson,\n\nI am referring Raj Patel (DOB: 1988-04-22, HN: 33591-8811) for cognitive-behavioural therapy. Mr. Patel was diagnosed with MDD (F32.1) in August 2023 and has demonstrated good pharmacological response to Sertraline 50mg (PHQ-9 reduced from 17 to 9). However, residual anhedonia and occupational impairment persist. An 8-session CBT course targeting negative automatic thoughts and behavioural activation is requested.\n\nDr. Bella Wu",
    faxNumber: "403-266-8800",
  },
  {
    id: "edoc-008",
    patientId: "33591",
    date: "2024-06-25",
    docType: "referral-letter",
    sender: "Wu, Bella — Family Practice, Calgary",
    recipient: "GI Clinic — Alberta Health Services, Calgary",
    status: "sent",
    subject: "Referral — Gastroenterology for GERD with Failed Lifestyle Management (Raj Patel)",
    content:
      "Dear Gastroenterology Colleagues,\n\nI am referring Raj Patel (DOB: 1988-04-22, HN: 33591-8811) for assessment of refractory GERD (K21.0). Mr. Patel has experienced ongoing heartburn and regurgitation despite 3 months of dietary modification. Pantoprazole 40mg has now been initiated with partial response. Please assess for consideration of upper endoscopy to exclude Barrett's oesophagus or erosive oesophagitis.\n\nDr. Bella Wu",
    faxNumber: "403-944-2800",
  },
  {
    id: "edoc-008-b",
    patientId: "33591",
    date: "2024-07-15",
    docType: "lab-report",
    sender: "LifeLabs Calgary",
    recipient: "Wu, Bella — Family Practice, Calgary",
    status: "received",
    subject: "Lab Results — TSH, LFTs, Fasting Glucose (33591)",
    content:
      "PATIENT: Raj Patel | DOB: 1988-04-22 | REQUISITION: 33591-ANN-240922\n\nTSH: 1.8 mIU/L (normal 0.4-4.5)\nALT: 28 U/L | AST: 22 U/L (both normal)\nFasting Glucose: 5.2 mmol/L (normal)\nVitamin D 25-OH: 58 nmol/L (normalized from 42)\n\nNo abnormalities detected.",
    faxNumber: "403-777-2200",
  },

  // ─── Sophie Dubois (57720) ───────────────────────────────────────────────────
  {
    id: "edoc-009",
    patientId: "57720",
    date: "2024-07-30",
    docType: "referral-letter",
    sender: "Wu, Bella — Family Practice, Sherwood Park",
    recipient: "Dr. M. Ng — Allergist, Edmonton",
    status: "sent",
    subject: "Referral — Allergy Assessment for OIT Candidacy (Sophie Dubois)",
    content:
      "Dear Dr. Ng,\n\nI am referring Sophie Dubois (DOB: 2005-11-30, HN: 57720-4430) for assessment for oral immunotherapy (OIT) candidacy for tree nut allergy. Ms. Dubois has a confirmed severe tree nut allergy (T78.1) with anaphylaxis history (September 2023 — EpiPen administered). Concurrent atopic dermatitis is currently controlled. Patient and family are motivated for desensitization. Please advise on suitability.\n\nDr. Bella Wu",
    faxNumber: "780-423-5500",
  },
  {
    id: "edoc-010",
    patientId: "57720",
    date: "2023-09-07",
    docType: "discharge-summary",
    sender: "Emergency Department — Grey Nuns Hospital, Edmonton",
    recipient: "Wu, Bella — Family Practice, Sherwood Park",
    status: "received",
    subject: "Discharge Summary — Anaphylaxis (Sophie Dubois, 2023-09-05)",
    content:
      "PATIENT: Sophie Dubois | DOB: 2005-11-30 | MRN: GNH-57720\nADMISSION: 2023-09-05 19:30 | DISCHARGE: 2023-09-05 23:45\n\nPRESENTING COMPLAINT: Anaphylaxis following accidental tree nut ingestion at restaurant.\n\nTREATMENT:\n- EpiPen 0.3mg IM (self-administered prior to arrival)\n- Epinephrine 0.5mg IM x1 in ED\n- Diphenhydramine 50mg IV\n- Methylprednisolone 125mg IV\n- IV NS 1L\n\nOBSERVATION: 4 hours post-treatment — no biphasic reaction. O2 sat normalised to 99% RA.\n\nDISCHARGE CONDITION: Stable.\nFOLLOW-UP: Family physician within 1 week.",
    faxNumber: "780-735-7000",
  },
  {
    id: "edoc-010-b",
    patientId: "57720",
    date: "2024-04-14",
    docType: "lab-report",
    sender: "LifeLabs Edmonton",
    recipient: "Wu, Bella — Family Practice, Sherwood Park",
    status: "received",
    subject: "Lab Results — Skin Swab Culture (57720)",
    content:
      "PATIENT: Sophie Dubois | DOB: 2005-11-30 | REQUISITION: 57720-SWAB-240411\n\nSPECIMEN: Skin swab — bilateral forearms\nCULTURE: No growth after 48 hours\nMRSA SCREEN: Negative\n\nCOMMENT: No evidence of bacterial superinfection. Results support diagnosis of non-infected atopic dermatitis.",
    faxNumber: "780-458-2200",
  },

  // ─── Gerald Morrison (68103) ─────────────────────────────────────────────────
  {
    id: "edoc-011",
    patientId: "68103",
    date: "2024-04-03",
    docType: "imaging-report",
    sender: "Cardiology — Dr. R. Kapoor, University of Alberta Hospital",
    recipient: "Chen, James — Family Practice, Leduc",
    status: "received",
    subject: "Echocardiography Report — Gerald Morrison (2024-04-03)",
    content:
      "PATIENT: Gerald Morrison | DOB: 1956-07-04 | MRN: UAH-68103\nSTUDY: Transthoracic Echocardiogram\nDATE: 2024-04-03\n\nFINDINGS:\n- LVEF: 38% (mildly reduced)\n- Global hypokinesis, no segmental wall motion abnormality\n- Mild mitral regurgitation (vena contracta 3mm)\n- Left atrium mildly dilated (LAD 43mm) — consistent with long-standing AFib\n- No pericardial effusion\n- IVC: mildly dilated, consistent with elevated RA pressure\n\nIMPRESSION: Mildly reduced LVEF, stable compared with prior study (40%). Findings consistent with non-ischaemic cardiomyopathy in the setting of long-standing AFib.\n\nDr. R. Kapoor, FRCPC",
    faxNumber: "780-407-6700",
  },
  {
    id: "edoc-012",
    patientId: "68103",
    date: "2024-04-05",
    docType: "referral-letter",
    sender: "Cardiology — Dr. R. Kapoor, University of Alberta Hospital",
    recipient: "Chen, James — Family Practice, Leduc",
    status: "received",
    subject: "Cardiology Consultation Letter — Gerald Morrison",
    content:
      "Dear Dr. Chen,\n\nThank you for referring Mr. Gerald Morrison (DOB: 1956-07-04) for cardiology review. I reviewed him in clinic on 2024-04-03.\n\nSUMMARY: Echo shows LVEF 38% (stable). Holter confirms rate-controlled AFib (average 66 bpm). INR is therapeutic on Warfarin.\n\nRECOMMENDATIONS:\n1. Continue current Bisoprolol dose for rate control.\n2. Consider adding Empagliflozin 10mg daily for HFrEF mortality benefit — appropriate given eGFR 20+.\n3. Annual echo in 12 months.\n4. Repeat Holter if symptomatic palpitations recur.\n\nThank you for this referral.\nDr. R. Kapoor, FRCPC Cardiology",
    faxNumber: "780-407-6700",
  },
  {
    id: "edoc-013",
    patientId: "68103",
    date: "2024-09-06",
    docType: "imaging-report",
    sender: "Radiology Dept — Leduc Community Hospital",
    recipient: "Chen, James — Family Practice, Leduc",
    status: "pending",
    subject: "Chest X-Ray Preliminary Read — Gerald Morrison (2024-09-06)",
    content:
      "PATIENT: Gerald Morrison | DOB: 1956-07-04 | REQUISITION: 68103-CXR-240905\nSTUDY: PA and Lateral Chest X-Ray\nDATE: 2024-09-06\n\nPRELIMINARY FINDINGS (Pending final radiologist sign-off):\n- Cardiomegaly present (CTR ~0.58)\n- Increased interstitial markings bilaterally — possible pulmonary oedema\n- Small bilateral pleural effusions cannot be excluded\n- No pneumothorax. No focal consolidation.\n\nFINAL REPORT: Pending review by Dr. S. Alvarez, Radiology.",
    faxNumber: "780-980-4600",
  },
  {
    id: "edoc-014",
    patientId: "68103",
    date: "2023-09-04",
    docType: "discharge-summary",
    sender: "Internal Medicine — Royal Alexandra Hospital, Edmonton",
    recipient: "Chen, James — Family Practice, Leduc",
    status: "received",
    subject: "Discharge Summary — Acute Decompensated Heart Failure (Gerald Morrison)",
    content:
      "PATIENT: Gerald Morrison | DOB: 1956-07-04 | MRN: RAH-68103\nADMISSION: 2023-08-28 | DISCHARGE: 2023-09-04\nATTENDING: Dr. A. Fernandez, Internal Medicine\n\nADMISSION DIAGNOSIS: Acute decompensated heart failure (HFrEF, LVEF 40%), fluid overload.\n\nIN-HOSPITAL MANAGEMENT:\n- IV Furosemide 80mg BID x3 days, then PO 40mg daily\n- Spironolactone 25mg continued\n- Daily weights and fluid restriction 1.5L/day\n- INR monitored — remained therapeutic\n- Weight on discharge: 86 kg (down 5 kg from admission)\n\nDISCHARGE MEDICATIONS: As per home medications (no changes).\n\nFOLLOW-UP: Family physician within 2 weeks (urgent).\n\nDr. A. Fernandez, FRCPC Internal Medicine",
    faxNumber: "780-735-7000",
  },

  // ─── Harold Whitmore (24884) ─────────────────────────────────────────────────
  {
    id: "edoc-hw-001",
    patientId: "24884",
    date: "2018-07-08",
    docType: "referral-letter",
    sender: "Park, Eleanor — Riverside Family Health Clinic",
    recipient: "Springfield Eye Associates — Ophthalmology",
    status: "sent",
    subject: "Referral — Diabetic Retinopathy Screening (Harold Whitmore)",
    content:
      "Dear Ophthalmology Colleagues,\n\nI am referring Harold Whitmore (DOB: 1945-03-08, MRN: SMC-04471932) for annual diabetic retinopathy screening. Mr. Whitmore has type 2 diabetes mellitus (E11.9, diagnosed 2014), currently managed with metformin 1000mg BID with HbA1c 7.0%. He also has hypertension and dyslipidemia, both controlled. No current visual complaints.\n\nPlease perform a dilated fundus examination and advise on follow-up interval.\n\nKind regards,\nDr. Eleanor Park, Internal Medicine",
    faxNumber: "555-018-4455",
  },
  {
    id: "edoc-hw-002",
    patientId: "24884",
    date: "2010-09-20",
    docType: "lab-report",
    sender: "LifeLabs Springfield",
    recipient: "Park, Eleanor — Riverside Family Health Clinic",
    status: "received",
    subject: "Lab Results — Baseline Fasting Panel (Harold Whitmore)",
    content:
      "PATIENT: Harold Whitmore | DOB: 1945-03-08 | REQUISITION: 24884-BASE-100915\n\nHbA1c: 6.1% (H — pre-diabetes range)\nFasting Glucose: 118 mg/dL (H)\nLDL Cholesterol: 172 mg/dL (H)\nHDL Cholesterol: 38 mg/dL (L)\nTriglycerides: 210 mg/dL (H)\nTotal Cholesterol: 248 mg/dL (H)\nCreatinine: 1.0 mg/dL | eGFR: 78 mL/min/1.73m2\nTSH: 2.2 mIU/L (normal)\nUrinalysis: no proteinuria, no glycosuria\n\nINTERPRETATION: Pre-diabetes (HbA1c 6.1%) with significant dyslipidemia. Recommend statin therapy and lifestyle intervention.\n\nVerified by LifeLabs Pathology",
    faxNumber: "555-018-4490",
  },
  {
    id: "edoc-hw-003",
    patientId: "24884",
    date: "2022-04-19",
    docType: "referral-letter",
    sender: "Park, Eleanor — Riverside Family Health Clinic",
    recipient: "Dr. R. Halloway — Cardiology, Springfield General",
    status: "sent",
    subject: "Referral — Cardiology Surveillance (Harold Whitmore)",
    content:
      "Dear Dr. Halloway,\n\nI am referring Harold Whitmore (DOB: 1945-03-08, MRN: SMC-04471932) for cardiology assessment and ongoing surveillance. He presents with mild exertional dyspnea and palpitations. Echocardiogram shows preserved EF (52%) with mild concentric LVH; 24-hour Holter shows occasional PACs without sustained arrhythmia. I have started bisoprolol 2.5mg daily.\n\nBackground: long-standing hypertension, type 2 diabetes, dyslipidemia, early CKD stage 2 (eGFR 68).\n\nThank you for your assessment.\nDr. Eleanor Park, Internal Medicine",
    faxNumber: "555-018-4470",
  },
  {
    id: "edoc-hw-004",
    patientId: "24884",
    date: "2013-06-15",
    docType: "lab-report",
    sender: "GI Associates Springfield",
    recipient: "Park, Eleanor — Riverside Family Health Clinic",
    status: "received",
    subject: "Colonoscopy Report — Screening (Harold Whitmore)",
    content:
      "PATIENT: Harold Whitmore | DOB: 1945-03-08 | MRN: SMC-04471932\nPROCEDURE: Screening colonoscopy\nDATE: 2013-06-15\nENDOSCOPIST: Dr. M. Trent, Gastroenterology\n\nFINDINGS:\n- Cecum reached; good prep quality.\n- Two diminutive (3-4 mm) sessile polyps in the sigmoid colon — removed by cold snare.\n- No masses, no significant diverticulosis.\n\nHISTOLOGY: Tubular adenomas, low-grade dysplasia, completely excised.\n\nRECOMMENDATION: Repeat surveillance colonoscopy in 5 years.\n\nDr. M. Trent, FRCPC Gastroenterology",
    faxNumber: "555-018-4480",
  },
];

export function getEDocumentsByPatientId(patientId: string): EDocument[] {
  return eDocuments.filter((d) => d.patientId === patientId);
}

export function getEDocumentById(id: string): EDocument | undefined {
  return eDocuments.find((d) => d.id === id);
}
