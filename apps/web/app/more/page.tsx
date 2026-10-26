import Link from "next/link";
export default function MorePage(){return <><h1>More</h1><nav className="ux-more mt-6" aria-label="More pages">{[["/programs","Programs"],["/customize","Customize"],["/checkin","Check-In"],["/analytics","Analytics"],["/guides","Exercise library"],["/settings","Settings & account"]].map(([href,label])=><Link key={href} href={href}>{label}</Link>)}</nav></>;}
