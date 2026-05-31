import { CircleDollarSign } from "lucide-react";

import { ComingSoon } from "../../../../../components/layout/ComingSoon";

export default function BillingTab() {
  return (
    <ComingSoon
      icon={CircleDollarSign}
      title="Billing"
      description="Claims chart and detail drawer. Billing is out-of-scope for the umraa backend so this tab will stay placeholder unless a billing endpoint is added."
    />
  );
}
