import { Suspense } from "react";

import { ArScreen } from "@/components/screens/ArScreen";

export default function Page() {
  return (
    <Suspense>
      <ArScreen />
    </Suspense>
  );
}
