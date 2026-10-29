import React from "react";
import { Outlet } from "react-router-dom";
import { PublicHeader } from "./PublicHeader";
import { PublicFooter } from "./PublicFooter";

export const AppLayout: React.FC = () => {
  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground antialiased selection:bg-primary/20">
      <PublicHeader />
      <main className="flex-1 flex flex-col w-full">
        <Outlet />
      </main>
      <PublicFooter />
    </div>
  );
};
