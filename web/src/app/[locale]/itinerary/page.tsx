import { Suspense } from "react";

import { ItineraryScreen } from "@/components/screens/ItineraryScreen";

export default function Page() {
  return (
    <Suspense>
      <ItineraryScreen />
    </Suspense>
  );
}
