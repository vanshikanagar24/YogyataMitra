"use client";

import React from "react";
import { Loader2, AlertTriangle, Inbox, RefreshCw } from "lucide-react";
import { useLanguage } from "../../context/LanguageContext";

export const LoadingState: React.FC<{ message?: string }> = ({ message }) => {
  const { t } = useLanguage();
  return (
    <div
      className="flex flex-col items-center justify-center py-16 text-center"
      role="status"
      aria-live="polite"
    >
      <Loader2 className="w-8 h-8 text-primary animate-spin mb-3" aria-hidden="true" />
      <p className="text-sm text-gov-secondary font-medium">
        {message || t("common.loading")}
      </p>
    </div>
  );
};

export const SchemeCardSkeleton: React.FC = () => {
  return (
    <div
      className="bg-white rounded-lg border border-gov-border p-6 shadow-gov-card space-y-4 animate-pulse"
      aria-hidden="true"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-2 flex-grow">
          <div className="h-5 bg-gray-200 rounded w-1/4" />
          <div className="h-6 bg-gray-200 rounded w-3/4" />
        </div>
        <div className="h-6 bg-gray-200 rounded-full w-20 flex-shrink-0" />
      </div>
      <div className="h-4 bg-gray-200 rounded w-1/2" />
      <div className="space-y-1.5 pt-2">
        <div className="h-3.5 bg-gray-200 rounded w-full" />
        <div className="h-3.5 bg-gray-200 rounded w-5/6" />
      </div>
      <div className="h-10 bg-gray-200 rounded w-full" />
      <div className="pt-4 border-t border-gray-100 flex items-center justify-between">
        <div className="h-4 bg-gray-200 rounded w-24" />
        <div className="h-8 bg-gray-200 rounded w-28" />
      </div>
    </div>
  );
};

export const TableSkeleton: React.FC<{ rows?: number }> = ({ rows = 3 }) => {
  return (
    <div className="bg-white rounded-lg border border-gov-border p-6 shadow-gov-card space-y-4 animate-pulse" aria-hidden="true">
      <div className="h-6 bg-gray-200 rounded w-1/3 mb-4" />
      <div className="space-y-3">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="h-12 bg-gray-100 rounded flex items-center px-4 space-x-4">
            <div className="h-4 bg-gray-200 rounded w-1/6" />
            <div className="h-4 bg-gray-200 rounded w-1/4" />
            <div className="h-4 bg-gray-200 rounded w-1/4" />
            <div className="h-4 bg-gray-200 rounded w-1/3" />
          </div>
        ))}
      </div>
    </div>
  );
};

export const ErrorState: React.FC<{
  title?: string;
  message?: string;
  onRetry?: () => void;
}> = ({ title, message, onRetry }) => {
  const { t } = useLanguage();
  return (
    <div
      className="bg-red-50 border border-red-200 rounded-lg p-6 my-6 text-center max-w-xl mx-auto"
      role="alert"
    >
      <AlertTriangle className="w-10 h-10 text-danger mx-auto mb-2" aria-hidden="true" />
      <h3 className="text-base font-bold text-danger-700 mb-1">
        {title || t("common.error")}
      </h3>
      <p className="text-xs text-gov-secondary mb-4 leading-relaxed">
        {message || t("common.error")}
      </p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="inline-flex items-center space-x-1.5 px-4 py-2 bg-white border border-gov-border rounded-md text-xs font-semibold text-gov-text hover:bg-gray-50 shadow-xs focus-visible:ring-2 focus-visible:ring-primary min-h-[36px]"
        >
          <RefreshCw className="w-3.5 h-3.5 text-gov-secondary" aria-hidden="true" />
          <span>{t("common.retry")}</span>
        </button>
      )}
    </div>
  );
};

export const EmptyState: React.FC<{
  title?: string;
  description?: string;
  action?: React.ReactNode;
}> = ({ title, description, action }) => {
  const { t } = useLanguage();
  return (
    <div
      className="bg-white border border-gov-border rounded-lg p-10 text-center max-w-md mx-auto my-8"
      role="region"
      aria-label={title || t("common.no_data")}
    >
      <Inbox className="w-12 h-12 text-gray-300 mx-auto mb-3" aria-hidden="true" />
      <h3 className="text-base font-bold text-gov-text mb-1">
        {title || t("common.no_data")}
      </h3>
      {description && (
        <p className="text-xs text-gov-secondary mb-4 leading-relaxed">
          {description}
        </p>
      )}
      {action}
    </div>
  );
};
