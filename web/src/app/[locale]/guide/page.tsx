import { Suspense } from "react";

import { GuideScreen } from "@/components/screens/GuideScreen";

export default function Page() {
  return (
    <Suspense>
      <GuideScreen />
    </Suspense>
  );
}
