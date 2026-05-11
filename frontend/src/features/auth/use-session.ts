import { useQuery } from "@tanstack/react-query";

import { getMe } from "@/api/auth";
import { useAuthStore } from "@/stores/auth-store";

export function useSession() {
  const accessToken = useAuthStore((state) => state.accessToken);
  const setUser = useAuthStore((state) => state.setUser);
  return useQuery({
    queryKey: ["session"],
    queryFn: async () => {
      const user = await getMe();
      setUser(user);
      return user;
    },
    enabled: Boolean(accessToken),
    retry: false,
  });
}
