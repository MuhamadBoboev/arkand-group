import { type ReactNode } from "react";
import { PersistQueryClientProvider } from "@tanstack/react-query-persist-client";
import { createSyncStoragePersister } from "@tanstack/query-sync-storage-persister";
import { queryClient } from "@/shared/api/query";

// Персист кеша (§6.1) — мгновенный старт после перезагрузки.
const persister = createSyncStoragePersister({
  storage: window.localStorage,
  key: "arkand-query-cache",
});

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <PersistQueryClientProvider
      client={queryClient}
      persistOptions={{ persister, maxAge: 1000 * 60 * 60 }}
    >
      {children}
    </PersistQueryClientProvider>
  );
}
