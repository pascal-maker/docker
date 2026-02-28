import { useContext } from "react";
import { ConsentContext } from "@/contexts/ConsentContext.tsx";

export function useConsent() {
  const ctx = useContext(ConsentContext);
  if (ctx == null) {
    throw new Error("useConsent must be used within ConsentProvider");
  }
  return ctx;
}
