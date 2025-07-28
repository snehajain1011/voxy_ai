import { NextRequest, NextResponse } from "next/server";
import { auth } from "./server/auth";

export async function middleware(request: NextRequest) {
  const session = await auth();
  const path = request.nextUrl.pathname;
  const isAuthRoute = path === "/app/sign-in" || path === "/app/sign-up";
  const isProtectedRoute = path.startsWith("/app/") && !isAuthRoute;
  if (session && isAuthRoute) {
    return NextResponse.redirect(
      new URL("/app/speech-synthesis/text-to-speech", request.url),
    );
  }
  if (!session && isProtectedRoute) {
    const signInUrl = new URL("/app/sign-in", request.url);
    signInUrl.searchParams.set("callbackUrl", request.url);
    return NextResponse.redirect(signInUrl);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/app/:path*"],
};
