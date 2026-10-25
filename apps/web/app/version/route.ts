// Compiled into the immutable web artifact, independent of the API response.
// Qualified main releases verify this build identifier after cutover.
export const dynamic = "force-static";

export function GET() {
  const version = process.env.NEXT_PUBLIC_APP_VERSION || "dev";
  return Response.json({ version }, { headers: { "Cache-Control": "no-store" } });
}
