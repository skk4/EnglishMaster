"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { User, clearAuth, getUser } from "@/lib/auth";

export function useAuth(): { user: User | null; loading: boolean } {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    try {
      const u = getUser();
      if (u) {
        setUser(u);
        setLoading(false);
      } else {
        // Not logged in — redirect unless already on /login
        if (pathname !== "/login") {
          router.push("/login");
        }
        setLoading(false);
      }
    } catch (e) {
      console.error("useAuth: failed to read user", e);
      clearAuth();
      if (pathname !== "/login") {
        router.push("/login");
      }
      setLoading(false);
    }
  }, [router, pathname]);

  return { user, loading };
}
