"use client";
import { useParams } from "next/navigation";
import { ProgramGuide } from "../program-guide";
export default function ProgramGuidePage() {
  const params = useParams();
  return <ProgramGuide programId={params?.programId as string | undefined} view="program" />;
}
