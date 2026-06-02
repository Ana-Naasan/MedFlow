import NextAuth from "next-auth"
import Credentials from "next-auth/providers/credentials"

interface MockDoctor {
  id: string
  email: string
  password: string
  name: string
  role: string
}

interface MockPatientUser {
  id: string
  email: string
  password: string
  name: string
}

const MOCK_DOCTORS: ReadonlyArray<MockDoctor> = [
  {
    id: "1",
    email: "dr.wu@umraa.ca",
    password: "password123",
    name: "Dr. Bella Wu",
    role: "Family Physician",
  },
  {
    id: "2",
    email: "dr.chen@umraa.ca",
    password: "password123",
    name: "Dr. James Chen",
    role: "Internist",
  },
] as const

const MOCK_PATIENTS: ReadonlyArray<MockPatientUser> = [
  {
    id: "p1",
    email: "patient@umraa.ca",
    password: "password123",
    name: "Alex Morgan",
  },
  {
    id: "p2",
    email: "member@umraa.ca",
    password: "password123",
    name: "Jordan Lee",
  },
] as const

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [
    Credentials({
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
        userType: { label: "User Type", type: "text" },
      },
      async authorize(credentials) {
        const email = credentials?.email as string | undefined
        const password = credentials?.password as string | undefined
        const userType = (credentials?.userType as string | undefined) ?? "clinician"

        if (!email || !password) {
          return null
        }

        if (userType === "patient") {
          const patient = MOCK_PATIENTS.find(
            (p) => p.email === email && p.password === password
          )
          if (!patient) return null
          return {
            id: patient.id,
            name: patient.name,
            email: patient.email,
            role: "Patient",
            userType: "patient" as const,
          }
        }

        const doctor = MOCK_DOCTORS.find(
          (d) => d.email === email && d.password === password
        )
        if (!doctor) return null

        return {
          id: doctor.id,
          name: doctor.name,
          email: doctor.email,
          role: doctor.role,
          userType: "clinician" as const,
        }
      },
    }),
  ],
  pages: {
    signIn: "/login/clinician",
  },
  callbacks: {
    jwt({ token, user }) {
      if (user) {
        const u = user as typeof user & {
          role?: string
          userType?: "patient" | "clinician"
        }
        token.role = u.role
        token.userType = u.userType ?? "clinician"
      }
      return token
    },
    session({ session, token }) {
      if (token.role && typeof token.role === "string") {
        session.user.role = token.role
      }
      if (token.userType === "patient" || token.userType === "clinician") {
        session.user.userType = token.userType
      }
      return session
    },
  },
})
