"use client";
import {useEffect, useState} from "react";
import {getToken} from "@/lib/api";

export function useHistoryAccount() {
  const [account, setAccount] = useState(getToken);
  useEffect(() => {
    const sync = () => setAccount(getToken());
    const storage = (event:StorageEvent) => { if(event.key === "hypertrophy_token" || event.key === null) sync(); };
    window.addEventListener("hypertrophy:auth-token-changed", sync);
    window.addEventListener("storage", storage);
    sync();
    return () => {window.removeEventListener("hypertrophy:auth-token-changed", sync); window.removeEventListener("storage", storage);};
  }, []);
  return account;
}

export function calendarDate(value:string) {
  const parsed = new Date(`${value}T00:00:00Z`);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value) || !Number.isFinite(parsed.getTime()) || parsed.toISOString().slice(0,10) !== value) throw new Error("Invalid calendar date");
  return parsed;
}
export function displayDate(value:string, options:Intl.DateTimeFormatOptions={weekday:"long",month:"long",day:"numeric"}) {
  return calendarDate(value).toLocaleDateString("en-US", {...options,timeZone:"UTC"});
}
export function historyRange(today:string, mode:"week"|"month", offset:number) {
  const start=calendarDate(today);
  if(mode === "week") {start.setUTCDate(start.getUTCDate()-((start.getUTCDay()+6)%7)+offset*7);}
  else {start.setUTCDate(1);start.setUTCMonth(start.getUTCMonth()+offset);}
  const end = new Date(start);
  if(mode === "week") end.setUTCDate(end.getUTCDate()+6);
  else {end.setUTCMonth(end.getUTCMonth()+1);end.setUTCDate(0);}
  return {startDate:start.toISOString().slice(0,10),endDate:end.toISOString().slice(0,10)};
}
export const historyStatusLabels = {complete:"Complete",partial:"Partial",scheduled:"Scheduled · not completed",rest:"Rest",unknown:"Unknown"} as const;
