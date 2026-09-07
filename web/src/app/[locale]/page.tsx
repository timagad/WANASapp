import { Suspense } from "react";

import { HomeScreen } from "@/components/screens/HomeScreen";

export default function Page() {
  return (
    <Suspense>
      <HomeScreen />
    </Suspense>
  );
}
