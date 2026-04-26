import { AlertCircle } from "lucide-react";

export function DashboardLoading() {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500" />
    </div>
  );
}

export function DashboardErro({ erro }) {
  return (
    <div className="p-6">
      <div className="flex items-center gap-2 text-red-600 bg-red-50 border border-red-200 rounded-lg p-4">
        <AlertCircle size={20} />
        <span>{erro}</span>
      </div>
    </div>
  );
}
