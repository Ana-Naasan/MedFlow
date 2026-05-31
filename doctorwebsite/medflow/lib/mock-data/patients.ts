import type { Patient } from "@/lib/types";

export const patients: Patient[] = [
  {
    id: "24884",
    name: { first: "Harold", last: "Whitmore" },
    dob: "1945-03-08",
    sex: "male",
    location: "Springfield, AB",
    healthNumber: "SMC-04471932",
    primaryPhysician: "Park, Eleanor",
    phone: "(555) 018-4400",
    email: "harold.whitmore@example.com",
    address: "2200 Riverside Parkway, Springfield, AB",
    allergies: [],
    medications: [
      { name: "Lisinopril 10mg", instructions: "Once daily", prescribedDate: "2010-09-15" },
      { name: "Atorvastatin 40mg", instructions: "Once nightly", prescribedDate: "2014-11-10" },
      { name: "Metformin 1000mg", instructions: "BID with meals", prescribedDate: "2014-11-10" },
      { name: "Bisoprolol 2.5mg", instructions: "Once daily", prescribedDate: "2022-04-19" },
      { name: "Aspirin 81mg", instructions: "Once daily", prescribedDate: "2010-09-15" },
    ],
    problems: [
      { code: "I10", description: "Essential hypertension", onsetDate: "2010-09-15", status: "active" },
      { code: "E11.9", description: "Type 2 diabetes mellitus without complications", onsetDate: "2014-11-10", status: "active" },
      { code: "E78.5", description: "Hyperlipidaemia, unspecified", onsetDate: "2010-10-13", status: "active" },
      { code: "E66.9", description: "Obesity, unspecified", onsetDate: "2010-09-15", status: "active" },
      { code: "F17.210", description: "Nicotine dependence, cigarettes, uncomplicated", onsetDate: "2010-09-15", status: "resolved" },
      { code: "N18.2", description: "Chronic kidney disease, stage 2", onsetDate: "2022-04-19", status: "active" },
    ],
    emergencyContacts: [
      { name: "Margaret Whitmore", relationship: "Spouse", phone: "(555) 018-4402" },
      { name: "Carol Whitmore", relationship: "Daughter", phone: "(555) 018-4403" },
    ],
    immunizationUpToDate: true,
  },
  {
    id: "10231",
    name: { first: "Margaret", last: "Chen" },
    dob: "1942-08-15",
    sex: "female",
    location: "Edmonton, AB",
    healthNumber: "10231-6542",
    familyPhysician: "Chen, James",
    primaryPhysician: "Chen, James",
    phone: "(780) 555-0201",
    email: "mchen@example.com",
    address: "22 Birch Crescent, Edmonton, AB T5K 1M3",
    allergies: [
      { name: "Sulfa drugs", severity: "severe", reaction: "Stevens-Johnson syndrome" },
      { name: "Codeine", severity: "mild", reaction: "Nausea" },
    ],
    medications: [
      { name: "Metformin 500mg", instructions: "BID with meals", prescribedDate: "2019-11-02" },
      { name: "Lisinopril 10mg", instructions: "Once daily", prescribedDate: "2020-03-18" },
      { name: "Atorvastatin 40mg", instructions: "Once nightly", prescribedDate: "2020-03-18" },
      { name: "ASA 81mg", instructions: "Once daily", prescribedDate: "2021-06-01" },
    ],
    problems: [
      { code: "E11.9", description: "Type 2 diabetes mellitus without complications", onsetDate: "2019-11-01", status: "active" },
      { code: "I10", description: "Essential (primary) hypertension", onsetDate: "2020-03-15", status: "active" },
      { code: "E78.5", description: "Hyperlipidaemia, unspecified", onsetDate: "2020-03-15", status: "active" },
      { code: "M54.5", description: "Low back pain", onsetDate: "2022-01-10", status: "resolved" },
    ],
    emergencyContacts: [
      { name: "David Chen", relationship: "Son", phone: "(780) 555-0202" },
    ],
    immunizationUpToDate: false,
  },
  {
    id: "33591",
    name: { first: "Raj", last: "Patel" },
    dob: "1988-04-22",
    sex: "male",
    location: "Calgary, AB",
    healthNumber: "33591-8811",
    primaryPhysician: "Wu, Bella",
    phone: "(403) 555-0301",
    email: "raj.patel@example.com",
    address: "89 Oak Avenue, Calgary, AB T2P 4K7",
    allergies: [],
    medications: [
      { name: "Sertraline 50mg", instructions: "Once daily in AM", prescribedDate: "2023-08-14" },
    ],
    problems: [
      { code: "F32.1", description: "Major depressive disorder, single episode, moderate", onsetDate: "2023-08-10", status: "active" },
      { code: "K21.0", description: "Gastro-oesophageal reflux disease with oesophagitis", onsetDate: "2022-02-05", status: "active" },
    ],
    emergencyContacts: [
      { name: "Priya Patel", relationship: "Spouse", phone: "(403) 555-0302" },
    ],
    immunizationUpToDate: true,
  },
  {
    id: "57720",
    name: { first: "Sophie", last: "Dubois" },
    dob: "2005-11-30",
    sex: "female",
    location: "Sherwood Park, AB",
    healthNumber: "57720-4430",
    familyPhysician: "Wu, Bella",
    primaryPhysician: "Wu, Bella",
    phone: "(780) 555-0401",
    email: "sdubois.guardian@example.com",
    address: "17 Cedar Lane, Sherwood Park, AB T8A 5N2",
    allergies: [
      { name: "Tree nuts", severity: "severe", reaction: "Anaphylaxis — carries EpiPen" },
    ],
    medications: [
      { name: "EpiPen 0.3mg auto-injector", instructions: "IM for anaphylaxis PRN", prescribedDate: "2018-06-01" },
      { name: "Cetirizine 10mg", instructions: "Once daily PRN allergies", prescribedDate: "2021-05-12" },
    ],
    problems: [
      { code: "L20.9", description: "Atopic dermatitis, unspecified", onsetDate: "2010-03-01", status: "active" },
      { code: "T78.1XXA", description: "Anaphylactic reaction — tree nuts", onsetDate: "2018-05-28", status: "active" },
    ],
    emergencyContacts: [
      { name: "Claire Dubois", relationship: "Mother", phone: "(780) 555-0402" },
      { name: "Marc Dubois", relationship: "Father", phone: "(780) 555-0403" },
    ],
    immunizationUpToDate: true,
  },
  {
    id: "68103",
    name: { first: "Gerald", last: "Morrison" },
    dob: "1956-07-04",
    sex: "male",
    location: "Leduc, AB",
    healthNumber: "68103-2295",
    familyPhysician: "Chen, James",
    primaryPhysician: "Chen, James",
    phone: "(780) 555-0501",
    email: "gmorrison@example.com",
    address: "5 Spruce Court, Leduc, AB T9E 6R1",
    allergies: [
      { name: "Aspirin", severity: "moderate", reaction: "GI bleeding" },
      { name: "Iodine contrast", severity: "severe", reaction: "Anaphylaxis" },
    ],
    medications: [
      { name: "Warfarin 5mg", instructions: "Once daily — INR monitoring required", prescribedDate: "2021-09-20" },
      { name: "Bisoprolol 5mg", instructions: "Once daily", prescribedDate: "2021-09-20" },
      { name: "Ramipril 10mg", instructions: "Once daily", prescribedDate: "2021-09-20" },
      { name: "Furosemide 40mg", instructions: "Once daily in AM", prescribedDate: "2022-01-05" },
      { name: "Spironolactone 25mg", instructions: "Once daily", prescribedDate: "2022-01-05" },
    ],
    problems: [
      { code: "I50.9", description: "Heart failure, unspecified", onsetDate: "2021-09-18", status: "active" },
      { code: "I48.91", description: "Unspecified atrial fibrillation", onsetDate: "2021-09-18", status: "active" },
      { code: "E11.65", description: "Type 2 diabetes mellitus with hyperglycaemia", onsetDate: "2015-04-22", status: "active" },
      { code: "N18.3", description: "Chronic kidney disease, stage 3", onsetDate: "2022-03-10", status: "active" },
    ],
    emergencyContacts: [
      { name: "Ruth Morrison", relationship: "Spouse", phone: "(780) 555-0502" },
      { name: "Kevin Morrison", relationship: "Son", phone: "(780) 555-0503" },
    ],
    immunizationUpToDate: false,
  },
];

export function getPatientById(id: string): Patient | undefined {
  return patients.find((p) => p.id === id);
}

export function searchPatients(query: string): Patient[] {
  const q = query.toLowerCase();
  return patients.filter(
    (p) =>
      p.name.first.toLowerCase().includes(q) ||
      p.name.last.toLowerCase().includes(q) ||
      p.id.includes(q) ||
      p.healthNumber.toLowerCase().includes(q)
  );
}
