import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { usersApi, type UserListParams } from "../api/users";

export function useUsers(params: UserListParams) {
  return useQuery({
    queryKey: ["users", params],
    queryFn: () => usersApi.list(params),
    placeholderData: keepPreviousData,
  });
}

export function useAgents() {
  return useQuery({ queryKey: ["users", "agents"], queryFn: usersApi.agents, staleTime: 5 * 60_000 });
}
