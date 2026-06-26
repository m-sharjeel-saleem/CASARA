import { AppTopbar } from "@/components/AppTopbar";
import { MobileNav, Sidebar } from "@/components/Sidebar";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <AppTopbar />
        <MobileNav />
        <main className="flex-1 px-5 py-7 sm:px-7">
          <div className="mx-auto max-w-6xl">{children}</div>
        </main>
      </div>
    </div>
  );
}
