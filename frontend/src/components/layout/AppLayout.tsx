import React from 'react';
import { Outlet, Link } from 'react-router-dom';

export default function AppLayout() {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-gray-50">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r flex flex-col hidden md:flex">
        <div className="p-4 border-b font-bold text-xl">TaxAutomation</div>
        <nav className="flex-1 p-4 space-y-2">
          <Link to="/" className="block p-2 hover:bg-gray-100 rounded">Engagements</Link>
          <Link to="/review" className="block p-2 hover:bg-gray-100 rounded">Review Queue</Link>
          <Link to="/results" className="block p-2 hover:bg-gray-100 rounded">Results</Link>
        </nav>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-16 border-b bg-white flex items-center px-4 justify-between">
          <div className="md:hidden font-bold">TaxAutomation</div>
          <div className="ml-auto flex items-center gap-4">
            <span className="text-sm">User</span>
          </div>
        </header>
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
