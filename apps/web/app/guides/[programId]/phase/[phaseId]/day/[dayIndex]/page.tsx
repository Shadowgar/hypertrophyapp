"use client";
import { useParams } from "next/navigation";
import { DayGuide } from "@/app/guides/day-guide";
export default function PhaseDayGuidePage() {
  const params = useParams();
  return <DayGuide programId={params?.programId as string | undefined} phaseId={params?.phaseId as string | undefined} dayParam={params?.dayIndex as string | undefined} />;
}
