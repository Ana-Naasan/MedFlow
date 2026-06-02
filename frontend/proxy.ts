import { auth } from "@/auth"

const PUBLIC_PATHS = new Set([
  "/",
  "/login",
  "/login/clinician",
  "/login/patient",
])

function isPublicPath(pathname: string): boolean {
  if (PUBLIC_PATHS.has(pathname)) return true
  if (pathname.startsWith("/login")) return true
  return false
}

/** Member app routes (/patient/...) — not clinician charts (/patients/...) */
function isPatientAppRoute(pathname: string): boolean {
  return pathname === "/patient" || pathname.startsWith("/patient/")
}

export default auth((req) => {
  const { pathname } = req.nextUrl
  const session = req.auth
  const userType = session?.user?.userType ?? "clinician"

  // Landing and login are always reachable (even when signed in)
  if (isPublicPath(pathname)) {
    return
  }

  if (!session) {
    const loginPath = isPatientAppRoute(pathname)
      ? "/login/patient"
      : "/login/clinician"
    return Response.redirect(new URL(loginPath, req.nextUrl.origin))
  }

  if (userType === "patient") {
    if (!isPatientAppRoute(pathname)) {
      return Response.redirect(
        new URL("/patient/dashboard", req.nextUrl.origin)
      )
    }
    return
  }

  if (isPatientAppRoute(pathname)) {
    return Response.redirect(new URL("/dashboard", req.nextUrl.origin))
  }
})

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
}
