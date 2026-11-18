"use client";
import { Amplify } from "aws-amplify";
import { Authenticator } from "@aws-amplify/ui-react";
import "@aws-amplify/ui-react/styles.css";

const userPoolId = process.env.NEXT_PUBLIC_USER_POOL_ID;
const userPoolClientId = process.env.NEXT_PUBLIC_USER_POOL_CLIENT_ID;

if (userPoolId && userPoolClientId) {
  Amplify.configure({ Auth: { Cognito: { userPoolId, userPoolClientId } } });
}

// Accounts are created by the agency with the client's ID attached, so there is no sign-up form:
// a self-registered user would have no client to look up.
export function Providers({ children }: { children: React.ReactNode }) {
  if (!userPoolId || !userPoolClientId) {
    return <p role="alert">Sign-in is not configured: set NEXT_PUBLIC_USER_POOL_ID and NEXT_PUBLIC_USER_POOL_CLIENT_ID in web/.env.local.</p>;
  }
  return <Authenticator hideSignUp>{children}</Authenticator>;
}
