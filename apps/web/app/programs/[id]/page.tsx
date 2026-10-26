"use client";
import { useParams } from "next/navigation";
import { ProgramGuide } from "@/app/guides/program-guide";
export default function ProgramDetailPage() {
  const params = useParams();
  return <ProgramGuide programId={params?.id as string | undefined} view="detail" />;
}
