/**
 * Componentes Skeleton para Loading States
 * Usado em dashboards e páginas com dados assíncronos
 */

export function KpiSkeleton() {
  return <div className="skeleton-shimmer skeleton-kpi" />;
}

export function ChartSkeleton({ height = 300 }) {
  return <div className="skeleton-shimmer" style={{ height }} />;
}

export function AnalyseSkeleton() {
  return <div className="skeleton-shimmer skeleton-analyse" />;
}

export function TextSkeleton({ short = false }) {
  return <div className={`skeleton ${short ? 'skeleton-text-short' : 'skeleton-text'}`} />;
}

export function CardSkeleton({ height = 110 }) {
  return (
    <div 
      className="skeleton-shimmer" 
      style={{ 
        height,
        padding: 16,
        border: '1px solid #e0e0e0',
        borderRadius: 8
      }} 
    />
  );
}
