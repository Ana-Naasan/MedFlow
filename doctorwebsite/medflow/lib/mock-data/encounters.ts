import type { Encounter } from "@/lib/types";
import { whitmoreEncounters } from "./whitmore-records";

export const encounters: Encounter[] = [
  // ─── Margaret Chen (10231) ───────────────────────────────────────────────────
  {
    id: "enc-005",
    patientId: "10231",
    date: "2024-02-08",
    type: "office-visit",
    physician: "Chen, James",
    chiefComplaint: "Quarterly diabetes and hypertension review",
    summary:
      "83-year-old female with T2DM, HTN, and hyperlipidaemia presenting for routine follow-up. HbA1c 7.8% (target <8%). BP well-controlled on current regimen. Lipid panel pending.",
    vitals: {
      bp: "138/82",
      hr: 74,
      temp: 36.7,
      weight: 64,
      height: 155,
      o2sat: 97,
      recordedAt: "2024-02-08T10:00:00",
    },
    soapNotes: {
      subjective:
        "Patient reports fatigue and mild polyuria. Denies chest pain, dyspnea, or visual changes. Diet has been less controlled over the holidays. No hypoglycaemic episodes. Medications taken as prescribed.",
      objective:
        "BP 138/82 mmHg (sitting). HR 74 bpm, regular. BMI 26.6. Bilateral pedal pulses intact. No peripheral edema. Fundoscopy deferred — referral to ophthalmology outstanding.",
      assessment:
        "T2DM (E11.9) — suboptimally controlled. HTN (I10) — controlled. Hyperlipidaemia (E78.5) — lipid panel ordered. Fatigue likely multifactorial (age, suboptimal glycaemia).",
      plan:
        "Increase Metformin to 1000mg BID. Repeat HbA1c in 3 months. Fasting lipid panel ordered. Referral to ophthalmology for annual diabetic eye exam. Reinforce low-glycaemic diet. Follow up in 3 months.",
    },
    prescriptions: ["Metformin 1000mg — BID with meals (dose increase)"],
  },
  {
    id: "enc-006",
    patientId: "10231",
    date: "2023-10-12",
    type: "office-visit",
    physician: "Chen, James",
    chiefComplaint: "Routine 3-month follow-up",
    summary:
      "Stable visit. HbA1c improved to 7.5% from 8.1%. BP slightly elevated at 148/88; Lisinopril dose unchanged pending repeat reading at next visit. Statin therapy continued.",
    vitals: {
      bp: "148/88",
      hr: 76,
      weight: 64.5,
      o2sat: 97,
      recordedAt: "2023-10-12T09:30:00",
    },
  },
  {
    id: "enc-007",
    patientId: "10231",
    date: "2024-05-20",
    type: "telehealth",
    physician: "Chen, James",
    chiefComplaint: "Dizziness and lightheadedness — possible orthostatic hypotension",
    summary:
      "Telehealth consult. Patient reports episodes of dizziness on standing, particularly in the morning. BP diary reviewed: range 110–130/70–80. Suspect orthostatic component. Advised to rise slowly, increase fluid intake. Home BP readings requested.",
  },
  {
    id: "enc-008",
    patientId: "10231",
    date: "2024-08-15",
    type: "office-visit",
    physician: "Chen, James",
    chiefComplaint: "Low back pain follow-up and medication review",
    summary:
      "Annual medication review. Low back pain now resolved. All chronic disease parameters reviewed. Immunization status flagged — influenza and pneumococcal vaccines overdue. Referral to podiatry placed for diabetic foot care.",
    vitals: {
      bp: "134/80",
      hr: 72,
      weight: 63.8,
      height: 155,
      o2sat: 98,
      recordedAt: "2024-08-15T11:15:00",
    },
  },

  // ─── Raj Patel (33591) ───────────────────────────────────────────────────────
  {
    id: "enc-009",
    patientId: "33591",
    date: "2024-03-05",
    type: "office-visit",
    physician: "Wu, Bella",
    chiefComplaint: "Depression follow-up — 6-month medication review",
    summary:
      "37-year-old male, MDD moderate. PHQ-9 score 9 (down from 17 at diagnosis). Reports improved sleep and mood on Sertraline. No side effects. Continue current regimen. Referral to psychology for CBT placed.",
    vitals: {
      bp: "122/78",
      hr: 68,
      temp: 36.5,
      weight: 82,
      height: 178,
      o2sat: 99,
      recordedAt: "2024-03-05T13:00:00",
    },
    soapNotes: {
      subjective:
        "Patient reports overall mood improvement over past 3 months. Sleep is better — averaging 7 hours/night vs 5 previously. Appetite restored. Energy levels improved at work. No suicidal ideation. Still experiencing occasional anhedonia on weekends. GERD symptoms well-controlled with dietary modifications.",
      objective:
        "Affect brighter than last visit. Good eye contact. Speech normal rate and volume. PHQ-9 = 9 (moderate). BP 122/78, HR 68 bpm. No somatic complaints. No signs of anxiety or agitation.",
      assessment:
        "MDD (F32.1) — improving on Sertraline 50mg. GERD (K21.0) — controlled with dietary modifications, no PPI currently required.",
      plan:
        "Continue Sertraline 50mg daily. Refer to clinical psychologist for 8-week CBT program. Monitor PHQ-9 at each visit. Reassess GERD — if symptoms recur, initiate Pantoprazole 40mg. Follow up in 3 months.",
    },
    prescriptions: ["Sertraline 50mg — once daily in AM (continue)"],
    attachedDocuments: ["edoc-007"],
  },
  {
    id: "enc-010",
    patientId: "33591",
    date: "2023-08-14",
    type: "office-visit",
    physician: "Wu, Bella",
    chiefComplaint: "Initial assessment — depressed mood and poor sleep",
    summary:
      "New presentation of depressive symptoms over 3 months. PHQ-9 score 17 (moderately severe). Initiated Sertraline 50mg. Safety assessment completed — no active suicidal ideation. Booked follow-up in 6 weeks.",
    vitals: {
      bp: "126/80",
      hr: 72,
      weight: 83,
      height: 178,
      o2sat: 99,
      recordedAt: "2023-08-14T09:45:00",
    },
  },
  {
    id: "enc-011",
    patientId: "33591",
    date: "2024-06-18",
    type: "telehealth",
    physician: "Wu, Bella",
    chiefComplaint: "GERD symptoms worsening — heartburn and regurgitation",
    summary:
      "Telehealth visit for recurrent GERD symptoms despite dietary changes. Initiated Pantoprazole 40mg daily. Advised to elevate head of bed and avoid late meals. Follow up in 4 weeks.",
    prescriptions: ["Pantoprazole 40mg — once daily before breakfast"],
  },
  {
    id: "enc-012",
    patientId: "33591",
    date: "2024-09-22",
    type: "office-visit",
    physician: "Wu, Bella",
    chiefComplaint: "Medication review — Sertraline and Pantoprazole",
    summary:
      "Annual review. PHQ-9 now 6 (mild). GERD well-controlled on Pantoprazole. Patient engaged in CBT program — 6 of 8 sessions completed. Discussed potential Sertraline dose increase if residual symptoms persist.",
    vitals: {
      bp: "120/76",
      hr: 65,
      weight: 80,
      height: 178,
      o2sat: 99,
      recordedAt: "2024-09-22T14:00:00",
    },
  },

  // ─── Sophie Dubois (57720) ───────────────────────────────────────────────────
  {
    id: "enc-013",
    patientId: "57720",
    date: "2024-04-11",
    type: "office-visit",
    physician: "Wu, Bella",
    chiefComplaint: "Eczema flare — bilateral arms and neck",
    summary:
      "19-year-old female presenting with 2-week eczema flare on bilateral arms and neck. Skin dry and erythematous with lichenification. No secondary infection. Prescribed topical corticosteroid and emollient.",
    vitals: {
      bp: "108/68",
      hr: 76,
      temp: 36.6,
      weight: 58,
      height: 163,
      o2sat: 99,
      recordedAt: "2024-04-11T11:00:00",
    },
    soapNotes: {
      subjective:
        "Reports worsening dry, itchy patches on arms and neck for 2 weeks. Aggravated by stress of upcoming university exams. Using moisturizer inconsistently. No new soap or detergent changes. EpiPen carried at all times. No anaphylaxis episodes this year.",
      objective:
        "Bilateral forearms and posterior neck: erythematous, lichenified plaques with excoriation. No vesicles, weeping, or signs of secondary bacterial infection. Remaining skin surfaces clear. EpiPen in bag confirmed.",
      assessment:
        "Atopic dermatitis (L20.9) — moderate flare, likely stress-triggered. Tree nut allergy (T78.1) — stable, no recent reactions.",
      plan:
        "Prescribe Hydrocortisone 1% cream BID for 2 weeks to affected areas. Continue daily emollient (Cetaphil). Reinforce EpiPen training. Referral to dermatology if no improvement in 4 weeks. Stress management discussed.",
    },
    prescriptions: ["Hydrocortisone 1% cream — apply BID to affected areas x 2 weeks"],
  },
  {
    id: "enc-014",
    patientId: "57720",
    date: "2023-09-05",
    type: "emergency",
    physician: "ER Staff",
    chiefComplaint: "Accidental nut exposure — anaphylaxis",
    summary:
      "Patient brought to ER after accidental ingestion of tree nut protein at a restaurant. EpiPen administered by patient prior to arrival. Treated with additional epinephrine and IV antihistamines. Monitored for 4 hours, discharged stable.",
    vitals: {
      bp: "88/58",
      hr: 118,
      temp: 37.2,
      o2sat: 93,
      recordedAt: "2023-09-05T19:45:00",
    },
  },
  {
    id: "enc-015",
    patientId: "57720",
    date: "2024-07-30",
    type: "office-visit",
    physician: "Wu, Bella",
    chiefComplaint: "Annual review — allergy management and eczema control",
    summary:
      "Annual review. Eczema stable with emollient routine. Referral to allergist for consideration of immunotherapy for tree nut desensitization. EpiPen prescription renewed.",
    vitals: {
      bp: "110/70",
      hr: 74,
      weight: 58.5,
      height: 163,
      o2sat: 99,
      recordedAt: "2024-07-30T10:30:00",
    },
    prescriptions: ["EpiPen 0.3mg auto-injector — carry at all times, renew x2"],
    attachedDocuments: ["edoc-009"],
  },

  // ─── Gerald Morrison (68103) ─────────────────────────────────────────────────
  {
    id: "enc-016",
    patientId: "68103",
    date: "2024-01-22",
    type: "office-visit",
    physician: "Chen, James",
    chiefComplaint: "Heart failure and CKD quarterly review",
    summary:
      "69-year-old male with heart failure (HFrEF), AFib on warfarin, T2DM with hyperglycaemia, and CKD stage 3. Presenting for quarterly review. INR therapeutic at 2.4. Creatinine stable at 168 umol/L. Mild ankle edema noted. Furosemide dose adjusted.",
    vitals: {
      bp: "126/78",
      hr: 64,
      temp: 36.5,
      weight: 89,
      height: 177,
      o2sat: 96,
      recordedAt: "2024-01-22T09:00:00",
    },
    soapNotes: {
      subjective:
        "Patient reports mild bilateral ankle swelling worsening over past 2 weeks. No orthopnea or PND. Dyspnea on exertion with >1 block walk. No chest pain or palpitations. Compliant with all medications. Low-sodium diet maintained. No bleeding events on warfarin.",
      objective:
        "BP 126/78. HR 64 bpm, irregular. JVP 4 cm above sternal angle. Bilateral pitting ankle edema 1+. Chest: bibasal fine crackles, reduced air entry at bases. Abdomen soft, no ascites. Weight 89 kg (up 2 kg from last visit).",
      assessment:
        "Heart failure (I50.9) — mild fluid overload. AFib (I48.91) — rate controlled, INR therapeutic. CKD stage 3 (N18.3) — stable. T2DM (E11.65) — HbA1c due for recheck.",
      plan:
        "Increase Furosemide to 80mg daily for 2 weeks, then return to 40mg. Repeat BMP in 1 week to monitor renal function and electrolytes. Repeat INR in 4 weeks. HbA1c and CMP ordered. Weight monitoring daily — return if >2 kg gain in 24h. Follow up in 6 weeks.",
    },
    prescriptions: ["Furosemide 80mg — daily x 2 weeks, then revert to 40mg"],
  },
  {
    id: "enc-017",
    patientId: "68103",
    date: "2023-09-18",
    type: "office-visit",
    physician: "Chen, James",
    chiefComplaint: "Post-hospitalization follow-up — heart failure exacerbation",
    summary:
      "Follow-up 2 weeks after hospital discharge for acute decompensated heart failure. Currently stable. Weight down 4 kg from discharge weight. Edema resolved. All medications restarted and tolerated.",
    vitals: {
      bp: "120/76",
      hr: 70,
      weight: 86,
      height: 177,
      o2sat: 97,
      recordedAt: "2023-09-18T10:00:00",
    },
  },
  {
    id: "enc-018",
    patientId: "68103",
    date: "2024-04-03",
    type: "specialist",
    physician: "Cardiology — Dr. R. Kapoor",
    chiefComplaint: "Cardiology follow-up — AFib rate control and HF management",
    summary:
      "Specialist cardiology review. Holter monitor completed showing rate-controlled AFib. Echo shows EF 38% (stable vs prior 40%). Bisoprolol dose unchanged. Discussed SGLT2 inhibitor addition for HFrEF benefit — to be initiated by family physician.",
    vitals: {
      bp: "128/80",
      hr: 66,
      o2sat: 96,
      weight: 88,
      recordedAt: "2024-04-03T14:30:00",
    },
    attachedDocuments: ["edoc-011", "edoc-012"],
  },
  {
    id: "enc-019",
    patientId: "68103",
    date: "2024-07-15",
    type: "office-visit",
    physician: "Chen, James",
    chiefComplaint: "Warfarin management — supratherapeutic INR",
    summary:
      "INR reported at 3.8 (target 2–3). No active bleeding. Warfarin held for 1 day then restarted at reduced dose 4mg. Dietary review — patient reports significantly increased green vegetable intake. Counselled on consistent vitamin K intake.",
    vitals: {
      bp: "130/82",
      hr: 68,
      weight: 88.5,
      o2sat: 97,
      recordedAt: "2024-07-15T11:00:00",
    },
  },
];

export function getEncountersByPatientId(patientId: string): Encounter[] {
  // Harold Whitmore's records are driven by his real PDF medical record.
  if (patientId === "24884") return whitmoreEncounters;
  return encounters.filter((e) => e.patientId === patientId);
}

export function getEncounterById(id: string): Encounter | undefined {
  return [...encounters, ...whitmoreEncounters].find((e) => e.id === id);
}
