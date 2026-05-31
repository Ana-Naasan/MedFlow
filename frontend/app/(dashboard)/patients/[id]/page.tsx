import { redirect } from "next/navigation";

// /patients/[id] has no content of its own — bounce to the Profile tab,
// matching medflow's behaviour.
export default function PatientIndex({ params }: { params: { id: string } }) {
  redirect(`/patients/${params.id}/profile`);
}
