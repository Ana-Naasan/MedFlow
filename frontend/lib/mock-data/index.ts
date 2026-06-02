// Re-exports all mock data arrays and helper functions

export { patients, getPatientById, searchPatients } from "./patients";
export { encounters, getEncountersByPatientId, getEncounterById } from "./encounters";
export { investigations, getInvestigationsByPatientId, getInvestigationById } from "./investigations";
export { notes, getNotesByPatientId, getNoteById } from "./notes";
export { billingEntries, getBillingByPatientId, getBillingEntryById, getBillingTotalByPatientId } from "./billing";
export { fileRecords, getFilesByPatientId, getFileById } from "./files";
export { eDocuments, getEDocumentsByPatientId, getEDocumentById } from "./edocuments";
