// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import BillingTab from "../app/(dashboard)/patients/[id]/billing/page";
import EDocumentsTab from "../app/(dashboard)/patients/[id]/edocuments/page";
import InvestigationsTab from "../app/(dashboard)/patients/[id]/investigations/page";
import NotesTab from "../app/(dashboard)/patients/[id]/notes/page";
import RecordsTab from "../app/(dashboard)/patients/[id]/records/page";
import MemosPage from "../app/(dashboard)/memos/page";
import SchedulerPage from "../app/(dashboard)/scheduler/page";
import TasksPage from "../app/(dashboard)/tasks/page";
import UtilitiesPage from "../app/(dashboard)/utilities/page";

/**
 * Coming-soon stub routes — these are intentionally light, so the test just
 * asserts each one renders a ComingSoon panel with its expected title. The
 * goal is to catch typos / missing imports during the IA migration.
 */
describe.each<[string, () => React.ReactElement, RegExp]>([
  ["Records", () => <RecordsTab />, /records/i],
  ["eDocuments", () => <EDocumentsTab />, /edocuments/i],
  ["Investigations", () => <InvestigationsTab />, /investigations/i],
  ["Notes", () => <NotesTab />, /notes/i],
  ["Billing", () => <BillingTab />, /billing/i],
  ["Scheduler", () => <SchedulerPage />, /scheduler/i],
  ["Memos", () => <MemosPage />, /memos/i],
  ["Tasks", () => <TasksPage />, /tasks/i],
  ["Utilities", () => <UtilitiesPage />, /utilities/i],
])("%s coming-soon stub", (_, Page, title) => {
  it("renders the ComingSoon panel with its title", () => {
    render(Page());
    expect(screen.getByTestId("coming-soon")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: title })).toBeInTheDocument();
    expect(screen.getByText(/coming soon/i)).toBeInTheDocument();
  });
});
