"use client";
import { useParams } from "next/navigation";
import { ProgramGuide } from "@/app/guides/program-guide";
export default function PhaseGuidePage() {
  const params = useParams();
  return <ProgramGuide programId={params?.programId as string | undefined} phaseId={params?.phaseId as string | undefined} view="phase" />;
}
