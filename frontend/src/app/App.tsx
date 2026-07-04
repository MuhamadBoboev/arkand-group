import { useEffect } from "react";
import { BrowserRouter } from "react-router-dom";
import { AppProviders } from "./providers/AppProviders";
import { useAuth } from "@/shared/model/auth.store";
import { startRealtimeSync } from "@/shared/api/query";
import { Toaster } from "@/shared/ui";
import { AppShell } from "@/widgets/app-shell";
import LoginPage from "@/pages/login/LoginPage";

function FullscreenLoader() {
  return (
    <div className="grid min-h-screen place-items-center bg-paper">
      <div className="flex flex-col items-center gap-3">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-crimson-200 border-t-brand" />
        <span className="text-sm text-neutral-500">Загрузка ARKAND…</span>
      </div>
    </div>
  );
}

function Root() {
  const { user, ready, loadMe } = useAuth();

  useEffect(() => {
    loadMe();
  }, [loadMe]);

  useEffect(() => {
    if (user) startRealtimeSync();
  }, [user]);

  if (!ready) return <FullscreenLoader />;
  if (!user) return <LoginPage />;
  return <AppShell />;
}

export function App() {
  return (
    <AppProviders>
      <BrowserRouter>
        <Root />
        <Toaster />
      </BrowserRouter>
    </AppProviders>
  );
}
